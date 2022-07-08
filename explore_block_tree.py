#!/usr/bin/env python3

import json
import pathlib
import sys
import argparse
import pathlib

vanilla_path_base = pathlib.Path.home() / ".steam/steam/steamapps/common/From The Depths/From_The_Depths_Data/StreamingAssets/Mods/Core_Structural"
vanilla_path_item = vanilla_path_base / "Items"
vanilla_path_itemdup = vanilla_path_base / "ItemDup"
vanilla_path_mesh = vanilla_path_base / "Meshes"

mod_base = pathlib.Path.home() / "From The Depths/Mods"
mega_slope_itemdup = mod_base / "MegaSlopesPack/ItemDup"
mega_slope_meshes = mod_base / "MegaSlopesPack/Meshes"
mega_slope_2_common_itemdup = mod_base / "MegaSlopesPack2CommonBlockMateri/ItemDup"
mega_slope_2_other_itemdup = mod_base / "MegaSlopesPack2OtherBlockMateria/ItemDup"
mega_slope_2_common_meshes = mod_base / "MegaSlopesPack2CommonBlockMateri/Meshes"
mega_slope_2_other_meshes = mod_base / "MegaSlopesPack2OtherBlockMateria/Meshes"

base_blocks = {}
blocks = {}
meshes = {}

def guid_for(block):
    return block["ComponentId"]["Guid"]

def load_files(path : pathlib.Path, glob_ptn : str, blocks : dict):
    i = 0
    for fn in path.glob(glob_ptn):
        with open(str(fn), "r") as f:
            item = json.load(f)
            guid = guid_for(item)
            blocks[guid] = item
            i += 1
    return i


load_files(vanilla_path_item, "*.item", base_blocks)
load_files(vanilla_path_itemdup, "*.itemduplicateandmodify", blocks)
load_files(vanilla_path_mesh, "*.mesh", meshes)
if load_files(mega_slope_2_common_itemdup, "*.itemduplicateandmodify", blocks) > 0:
    load_files(mega_slope_2_common_meshes, "*.mesh", meshes)
    load_files(mega_slope_2_other_itemdup, "*.itemduplicateandmodify", blocks)
    load_files(mega_slope_2_other_meshes, "*.mesh", meshes)
else:
    load_files(mega_slope_itemdup, "*.itemduplicateandmodify", blocks)
    load_files(mega_slope_meshes, "*.mesh", meshes)

by_base_block = {}
by_mesh = {}

for blk_guid, blk in blocks.items():
    base_blk_guid = blk["IdToDuplicate"]["Reference"]["Guid"]
    base_blk = base_blocks[base_blk_guid]

    if base_blk_guid not in by_base_block:
        by_base_block[base_blk_guid] = {}

    by_base_block[base_blk_guid][blk_guid] = blk

    mesh_guid = blk["MeshReference"]["Reference"]["Guid"]
    mesh = meshes[mesh_guid]

    if mesh_guid not in by_mesh:
        by_mesh[mesh_guid] = {}
    
    by_mesh[mesh_guid][blk_guid] = blk

for base_blk_guid, base_blk in base_blocks.items():
    print(f"{base_blk_guid} {base_blk['ComponentId']['Name']}")

print("-" * 50)
    
for base_blk_guid, blocks in by_base_block.items():
    base_blk = base_blocks[base_blk_guid]
    print(f"{base_blk_guid} {base_blk['ComponentId']['Name']}")
    for blk_guid, blk in blocks.items():
        print(f"    {blk_guid} {blk['ComponentId']['Name']}")

print("-" * 50)

for mesh_guid, blocks in by_mesh.items():
    mesh = meshes[mesh_guid]
    print(f"{mesh_guid} {mesh['ComponentId']['Name']}")
    for blk_guid, blk in blocks.items():
        base_blk_guid = blk["IdToDuplicate"]["Reference"]["Guid"]
        base_blk = base_blocks[base_blk_guid]
        print(f"    {blk_guid} {blk['ComponentId']['Name']} [{base_blk['ComponentId']['Name']}]")