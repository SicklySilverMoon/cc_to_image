from cc_tools import CC1
from cc_tools import CC1Level
from cc_tools import CC1Levelset
from cc_tools import DATHandler
from PIL import Image
from PIL import ImageDraw
from PIL import GifImagePlugin
import sys
import os
import argparse
import re

GifImagePlugin.LOADING_STRATEGY = GifImagePlugin.LoadingStrategy.RGB_ALWAYS

def load_images(tileset_folder):
    frames = 1
    framerate = None
    try:
        base_img = Image.open(os.path.join(tileset_folder, "tiles.gif"))#.convert("RGBA")
        frames = base_img.n_frames
        framerate = base_img.info["duration"]
    except FileNotFoundError:
        base_img = Image.open(os.path.join(tileset_folder, "tiles.png")).convert("RGBA")
    try:
        overlay_img = Image.open(os.path.join(tileset_folder, "overlay.gif"))#.convert("RGBA")
    except FileNotFoundError:
        overlay_img = Image.open(os.path.join(tileset_folder, "overlay.png")).convert("RGBA")
    tile_size = base_img.size[0] // 7
    bases = [[] for _ in range(7 * 16)]
    overlays = [[] for _ in range(7 * 16)]
    for x in range(7):
        for y in range(16):
            if frames == 1:
                bases[x * 16 + y].append(base_img.crop((x * tile_size, y * tile_size, (x+1) * tile_size, (y+1) * tile_size)))
                overlays[x * 16 + y].append(overlay_img.crop((x * tile_size, y * tile_size, (x+1) * tile_size, (y+1) * tile_size)))
            else:
                for f in range(frames):
                    base_img.seek(f)
                    overlay_img.seek(f)
                    bases[x * 16 + y].append(base_img.crop((x * tile_size, y * tile_size, (x+1) * tile_size, (y+1) * tile_size)))
                    overlays[x * 16 + y].append(overlay_img.crop((x * tile_size, y * tile_size, (x+1) * tile_size, (y+1) * tile_size)))
    base_img.close()
    overlay_img.close()
    return (bases, overlays, tile_size, frames, framerate)

def draw_map(img_out, level, base_tiles, overlay_tiles, tile_size, frame):
    for cell_num in range(len(level.map)):
        cell = level.map[cell_num]
        if cell.bottom == CC1.FLOOR:
            img_out.paste(im=base_tiles[cell.top.value][frame], box=(cell_num % 32 * tile_size, cell_num // 32 * tile_size))
        else:
            img_out.paste(im=base_tiles[cell.bottom.value][frame], box=(cell_num % 32 * tile_size, cell_num // 32 * tile_size))
            #img_out.alpha_composite(im=overlays[cell.top.value], dest=(cell_num % 32 * tile_size, cell_num // 32 * tile_size))
            img_out.paste(im=overlay_tiles[cell.top.value][frame], box=(cell_num % 32 * tile_size, cell_num // 32 * tile_size), mask=overlay_tiles[cell.top.value][frame])

def draw_connections(img_out, connections, tile_size, colour):
    draw = ImageDraw.Draw(img_out)
    for source_raw, dest_raw in connections:
        source = (source_raw % 32, source_raw // 32)
        dest = (dest_raw % 32, dest_raw // 32)
        #print(source)
        draw.line(((source[0] * tile_size + tile_size / 2, source[1] * tile_size + tile_size / 2), (dest[0] * tile_size + tile_size / 2, dest[1] * tile_size + tile_size / 2)), fill=colour)
        
def draw_toggles(img_out, level_map, tile_size, colour):
    draw = ImageDraw.Draw(img_out)
    buttons = []
    doors = []
    for cell_num in range(len(level_map)):
        cell = level_map[cell_num]
        if cell.top == CC1.GREEN_BUTTON:
            buttons.append((cell_num % 32, cell_num // 32))
        elif cell.top == CC1.TOGGLE_FLOOR or cell.top == CC1.TOGGLE_WALL:
            doors.append((cell_num % 32, cell_num // 32))
    for button in buttons:
        for door in doors:
            draw.line(((button[0] * tile_size + tile_size / 2, button[1] * tile_size + tile_size / 2), (door[0] * tile_size + tile_size / 2, door[1] * tile_size + tile_size / 2)), fill=colour)

def parse_get_range(str_in):
    pattern = re.compile(r"^([0-9]+)(?:-([0-9]+))?$$")
    match = pattern.match(str_in)
    if not match:
        raise ValueError("Must be either a single number or a range in the format \"123-456\"")
    if match.group(2) == None: #single digit
        return [int(match.group(1))]
    lower = int(match.group(1))
    upper = int(match.group(2))
    if lower > upper:
        raise ValueError("Lower end of range must be less than upper")
    return list(range(lower, upper + 1))

colours = {
    "RED" : (255, 0, 0),
    "GREEN" : (0, 255, 0),
    "BLUE" : (0, 0, 255),
    "YELLOW" : (255, 255, 0),
    "CYAN" : (0, 255, 255),
    "MAGENTA" : (255, 0, 255),
    "WHITE" : (255, 255, 255),
    "BLACK" : (0, 0, 0),
}

def main():
    #if len(sys.argv) < 4:
    #    print("usage: cc_to_image.py base_tiles overlay_tiles DAT")
    #    exit(1)
    
    parser = argparse.ArgumentParser(description="Generate maps of Chip's Challenge levels")
    #parser.add_argument("base_tiles", help="The path to the normal tiles (used when the bottom layer is floor)")
    #parser.add_argument("overlay_tiles", help="The path to the overlay tiles (used when the bottom layer is not floor, has transparent sections)")
    parser.add_argument("dat_file", help="The Chip's Challenge levelset to map")
    parser.add_argument("-t", "--tileset_folder", help="The path to the folder containing the tileset, must contain 2 file: \"tiles.png\" & \"overlay.png\"", default="tilesets/ms")
    parser.add_argument("-d", "--toggle_doors", help="Draw lines from ALL toggle buttons to ALL toggle doors (top layer only; pass with no value for magenta; not recommended)", choices=colours.keys(), default=None, nargs="?", const="MAGENTA")
    parser.add_argument("-c", "--connections", help="Draw lines from link buttons to connections, (pass with no value to disable)", choices=colours.keys(), default="RED", nargs="?", const=None)
    parser.add_argument("-l", "--levels", help="Levels to map, accepts ranges, ex. -l 1 3 5-7", type=parse_get_range, nargs="+", default=["all"])
    #todo: optional argument for levels, accepts both level numbers and ranges in the form A-B (B > A, inclusive), so it could go "--levels 1 3 5 10-15 20 22-24", should add a custom arg-parse handler/action to validate and collect into ranges
    args = parser.parse_args()
    
    bases, overlays, tile_size, frames, framerate = load_images(args.tileset_folder)
    
    try:
        os.mkdir("maps")
    except FileExistsError:
        pass
        
    try:
        dat_name = os.path.splitext(os.path.basename(args.dat_file))[0]
        #print(dat_name)
        os.mkdir(f"maps/{dat_name}")
    except FileExistsError:
        pass

    levelset = DATHandler.read(args.dat_file)
    
    #print(args.levels)
    if args.levels[0] != "all":
        levels = []
        for level_range in args.levels:
            for level in level_range:
                levels.append(level)
        levels = sorted(list(set(levels)))
    else:
        levels = parse_get_range(f"{1}-{len(levelset.levels)}")
    #print(levels)
    
    for i in levels:
    #for i in range(4,5):
        if i - 1 > len(levelset.levels):
            break
        images_out = []
        for f in range(frames):
            img_out = Image.new("RGBA", (tile_size * 32, tile_size * 32))
            level = levelset.levels[i - 1]
            
            draw_map(img_out, level, bases, overlays, tile_size, f)
            if args.toggle_doors != None:
                draw_toggles(img_out, level.map, tile_size, colours[args.toggle_doors])
            if args.connections != None:
                draw_connections(img_out, list(level.traps.items()) + list(level.cloners.items()), tile_size, colours[args.connections])
            
            images_out.append(img_out)
        if frames == 1:
            images_out[0].save(f"maps/{dat_name}/{i:05d}.png", "PNG")
        else:
            images_out[0].save(f"maps/{dat_name}/{i:05d}.gif", "GIF", save_all = True, append_images = images_out[1 : ], optimize = True, duration = framerate, loop=0)
    

if __name__ == "__main__":
    main()