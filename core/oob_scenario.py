"""Scenario export: transforms OOB data into game-compatible scenario files.

Extracted from OOBData.save_scenario() and the standalone _copy_templates().
"""

import os
import math
import shutil
from pathlib import Path

import pandas as pd

from constants import HIERARCHY_COLS, INT_COLUMNS


# Columns required in the game's scenario.csv format
SCENARIO_COLUMNS = [
    "userName", "id", "sideIndex", "armyIndex", "corpsIndex", "divisionIndex",
    "brigadeIndex", "regimentIndex", "battalionIndex",
    "ammo", "dirSouth", "dirEast", "south", "east", "formation",
    "headCount", "fatigue", "morale",
]

# Mapping from scenario column -> OOB column (None = generated)
SCENARIO_TO_OOB = {
    "userName": "NAME1",
    "id": "ID",
    "sideIndex": "SIDE 1",
    "armyIndex": "ARMY 2",
    "corpsIndex": "CORPS 3",
    "divisionIndex": "DIV 4",
    "brigadeIndex": "BGDE 5",
    "regimentIndex": "BTN 6",
    "battalionIndex": None,
    "ammo": "AMMO",
    "dirSouth": None,
    "dirEast": None,
    "south": None,
    "east": None,
    "formation": "Formation",
    "headCount": "Head Count",
    "fatigue": "Fatigue",
    "morale": "Morale",
}

MAPLOCATIONS_HEADER = [
    "Name", "ID", "Priority", "Type", "AI",
    "loc x", "loc z", "radius", "Men", "Points",
    "Fatigue", "Morale", "Ammo", "OccMod",
    "Beg", "End", "Interval", "Sprite",
    "Army1", "Army2", "Army3",
]

VC_SECTION_MAP = {
    "Major Victory": "endmajwin",
    "Minor Victory": "endwin",
    "Draw": "endtie",
    "Minor Defeat": "endfail",
    "Major Defeat": "endmajfail",
}


def export_scenario(oob_data, scenario_dir: str, map_name: str, oob_filename: str,
                    placed_units, objectives=None, intro_text: str = "",
                    start_time: str = "", victory_conditions: dict = None):
    """Export OOB data as a complete game scenario directory.

    Args:
        oob_data: OOBData instance with loaded data.
        scenario_dir: Destination directory path.
        map_name: Name of the game map (without extension).
        oob_filename: Original OOB CSV filename for the MASTER line.
        placed_units: List of dicts with row_index, world_x, world_y, rotation, formation.
        objectives: List of objective data dicts (with 'fields' key).
        intro_text: Custom intro text in game HTML format.
        start_time: Start time string (HH:MM:SS).
        victory_conditions: Dict of label -> points.
    """
    df = oob_data._df_sorted_by_hierarchy(oob_data.df.copy())
    if "line_number" in df.columns:
        df = df.drop(columns=["line_number"])

    scenario_df = pd.DataFrame()
    int_columns = set(HIERARCHY_COLS + INT_COLUMNS)

    for scenario_col in SCENARIO_COLUMNS:
        oob_col = SCENARIO_TO_OOB.get(scenario_col)
        if oob_col and oob_col in df.columns:
            if oob_col in int_columns:
                scenario_df[scenario_col] = df[oob_col].fillna(0)
            else:
                scenario_df[scenario_col] = df[oob_col].fillna("")
        else:
            scenario_df[scenario_col] = ""

    if placed_units:
        placed_lookup = {pu["row_index"]: pu for pu in placed_units}
        for i in scenario_df.index:
            if i in placed_lookup:
                pu = placed_lookup[i]
                south = -1 * math.cos(math.radians(pu["rotation"]))
                east = math.sin(math.radians(pu["rotation"]))
                scenario_df.at[i, "south"] = pu["world_y"]
                scenario_df.at[i, "east"] = pu["world_x"]
                scenario_df.at[i, "dirSouth"] = south
                scenario_df.at[i, "dirEast"] = east
                if pu.get("formation"):
                    scenario_df.at[i, "formation"] = pu["formation"]

    if placed_units:
        placed_row_indices = set(pu["row_index"] for pu in placed_units)
        scenario_df = scenario_df[scenario_df.index.isin(placed_row_indices)].reset_index(drop=True)

    os.makedirs(scenario_dir, exist_ok=True)
    path = os.path.join(scenario_dir, "scenario.csv")
    scenario_df.to_csv(path, encoding="cp1252", index=False)

    # Insert MASTER line
    with open(path, "r", encoding="cp1252") as f:
        lines = f.readlines()
    master_fields = ["MASTER", oob_filename] + [""] * (len(SCENARIO_COLUMNS) - 2)
    master_line = ",".join(master_fields) + "\n"
    lines.insert(1, master_line)
    with open(path, "w", encoding="cp1252") as f:
        f.writelines(lines)

    _copy_templates(scenario_dir)

    if intro_text:
        intro_path = os.path.join(scenario_dir, "EnglishScenIntro.txt")
        with open(intro_path, "w", encoding="cp1252") as f:
            f.write(intro_text)

    if objectives:
        maplocations_path = os.path.join(scenario_dir, "maplocations.csv")
        with open(maplocations_path, "w", encoding="cp1252") as f:
            f.write(",".join(MAPLOCATIONS_HEADER) + "\n")
            for obj in objectives:
                fields = obj.get("fields", {})
                row = ",".join(str(fields.get(col, "")) for col in MAPLOCATIONS_HEADER)
                f.write(row + "\n")

    if map_name or start_time or victory_conditions:
        _patch_scenario_ini(scenario_dir, map_name, start_time, victory_conditions)


def _patch_scenario_ini(scenario_dir: str, map_name: str, start_time: str,
                        victory_conditions: dict = None):
    ini_path = os.path.join(scenario_dir, "scenario.ini")
    if not os.path.exists(ini_path):
        return
    with open(ini_path, "r", encoding="cp1252") as f:
        lines = f.readlines()

    in_section = None
    vc_inserted = set()
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped[1:-1]
        elif in_section == "init" and stripped.startswith("map=") and map_name:
            lines[i] = f"map={map_name}\n"
        elif in_section == "init" and stripped.startswith("starttime=") and start_time:
            lines[i] = f"starttime={start_time}\n"
        elif (victory_conditions
              and in_section in VC_SECTION_MAP.values()
              and in_section not in vc_inserted):
            vc_label = {v: k for k, v in VC_SECTION_MAP.items()}.get(in_section)
            if vc_label and vc_label in victory_conditions and stripped.startswith("article="):
                points = victory_conditions[vc_label]
                lines.insert(i + 1, f"grade={points}\n")
                vc_inserted.add(in_section)

    with open(ini_path, "w", encoding="cp1252") as f:
        f.writelines(lines)


def _copy_templates(scenario_dir: str):
    """Copy template files from the templates/scenario/ folder into the scenario directory."""
    templates_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "templates", "scenario")
    for template_file in (
        "battlescript.csv",
        "EnglishScenIntro.txt",
        "EnglishScenScreen.txt",
        "maplocations.csv",
        "scenario.ini",
    ):
        src = os.path.join(templates_dir, template_file)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(scenario_dir, template_file))
