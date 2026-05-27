import re

def get_tga_dimensions(filepath):
    """Extract map width and height from a lsl file by searching for the header pattern for the packed tga file.
    
        Assumes that the dimensions are scaled by a Tile Scale of 512.
        If Tile Scale is set to 256 with a dimension of 512, the map will be half the size as expected.
        I do not know how to extract this field reliably, or even which file it is stored in."""
    footer = "TRUEVISION-XFILE".encode('utf-8')
    with open(filepath, 'rb') as f:
        content = f.read()
        max_position = content.find(footer) # If found, only search until tga footer to prevent extra matches.
    
    header = re.compile(b'\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    with open(filepath, 'rb') as f: 
        data = f.read(max_position)
        results = [{'offset': match.start(), 'width': int.from_bytes(data[match.start()+12:match.start()+14], 'little'), 'height': int.from_bytes(data[match.start()+14:match.start()+16], 'little')} for match in header.finditer(data)]
        filtered_results=[x for x in results if x['width']==x['height']] # should be square.
        filtered_results=[x for x in filtered_results if x['width']>0 and x['height']>0] # shouldn't be zero.
        final_results=[x for x in filtered_results if x['width']%256==0 and x['height']%256==0] # Probably should be a multiple of 256. Usually 512, 768, 1024.
        if len(final_results) > 1:
            print(f"Multiple valid headers found in {filepath}. Results: {final_results}. Returning the first one, good luck with that.")
        return final_results[0]['width'], final_results[0]['height']