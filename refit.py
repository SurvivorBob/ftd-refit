#!/usr/bin/env python3
"""
Performs material remapping on a blueprint.

License information:

   Copyright 2022 SurvivorBob <ftd-devoxelizer@survivorbob.xyz>

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

"""

import json
import pathlib
import sys
import argparse
import pathlib
import logging

logging.basicConfig(format='[%(asctime)s] [%(levelname)s] %(message)s', level=logging.DEBUG)

vanilla_path_base = pathlib.Path.home() / ".steam/steam/steamapps/common/From The Depths/From_The_Depths_Data/StreamingAssets/Mods/Core_Structural"
vanilla_path_item = vanilla_path_base / "Items"
vanilla_path_itemdup = vanilla_path_base / "ItemDup"

mod_base = pathlib.Path.home() / "From The Depths/Mods"
mega_slope_itemdup = mod_base / "MegaSlopesPack/ItemDup"
mega_slope_2_common_itemdup = mod_base / "MegaSlopesPack2CommonBlockMateri/ItemDup"
mega_slope_2_other_itemdup = mod_base / "MegaSlopesPack2OtherBlockMateria/ItemDup"

base_blocks = {}
blocks = {}

def block_for_guid(guid):
    if guid in base_blocks:
        return base_blocks[guid]
    if guid in blocks:
        return blocks[guid]
    return None

def name_for_guid(guid):
    blk = block_for_guid(guid)
    if blk is None:
        return "unknown block"
    return blk["ComponentId"]["Name"]

def guid_for(block):
    return block["ComponentId"]["Guid"]

def mesh_guid_for(block):
    return block["MeshReference"]["Reference"]["Guid"]

def base_block_guid_for(block):
    if guid_for(block) in base_blocks:
        return guid_for(block)
    return block["IdToDuplicate"]["Reference"]["Guid"]

def load_files(path : pathlib.Path, glob_ptn : str, blocks : dict):
    i = 0
    for fn in path.glob(glob_ptn):
        with open(str(fn), "r") as f:
            item = json.load(f)
            guid = guid_for(item)
            blocks[guid] = item
            i += 1
    return i

logging.info("loading block database...")

load_files(vanilla_path_item, "*.item", base_blocks)
load_files(vanilla_path_itemdup, "*.itemduplicateandmodify", blocks)
if load_files(mega_slope_2_common_itemdup, "*.itemduplicateandmodify", blocks) > 0:
    load_files(mega_slope_2_other_itemdup, "*.itemduplicateandmodify", blocks)
else:
    load_files(mega_slope_itemdup, "*.itemduplicateandmodify", blocks)

logging.info(f"loaded {len(base_blocks)} base blocks and {len(blocks)} derived blocks!")

by_base_block = {}
by_mesh = {}

logging.info("creating block mappings...")

for blk_guid, blk in blocks.items():
    base_blk_guid = blk["IdToDuplicate"]["Reference"]["Guid"]
    base_blk = base_blocks[base_blk_guid]

    if base_blk_guid not in by_base_block:
        by_base_block[base_blk_guid] = {}

    by_base_block[base_blk_guid][blk_guid] = blk

    mesh_guid = mesh_guid_for(blk)
    # mesh = meshes[mesh_guid]

    if mesh_guid not in by_mesh:
        by_mesh[mesh_guid] = {}
    
    by_mesh[mesh_guid][blk_guid] = blk

logging.info(f"created mappings for {len(by_mesh)} meshes!")

# W S G R A M H L
letter_to_baseblock_guid = {
    "W": guid_for([b for b in base_blocks.values() if 'Wood Block' == b['ComponentId']['Name']][0]),
    "S": guid_for([b for b in base_blocks.values() if 'Stone' in b['ComponentId']['Name']][0]),
    "A": guid_for([b for b in base_blocks.values() if 'Alloy' in b['ComponentId']['Name']][0]),
    "M": guid_for([b for b in base_blocks.values() if 'Metal' in b['ComponentId']['Name']][0]),
    "H": guid_for([b for b in base_blocks.values() if 'Heavy' in b['ComponentId']['Name']][0]),
    "G": guid_for([b for b in base_blocks.values() if 'Glass' in b['ComponentId']['Name']][0]),
    "R": guid_for([b for b in base_blocks.values() if 'Rubber' in b['ComponentId']['Name']][0]),
    "L": guid_for([b for b in base_blocks.values() if 'Lead' in b['ComponentId']['Name']][0]),
}

def parse_op(op):
    ret = {
        'fromBaseBlockGuid': None,
        'fromColor': None,
        'toBaseBlockGuid': None,
        'toColor': None
    }
    to_parse = op[:]

    if len(to_parse) == 0:
        return ret

    l, to_parse = to_parse[0], to_parse[1:]
    if l in letter_to_baseblock_guid:
        ret['fromBaseBlockGuid'] = letter_to_baseblock_guid[l]
    
    d = ''
    while len(to_parse) > 0 and to_parse[0].isdigit():
        d = d + to_parse[0]
        to_parse = to_parse[1:]
    if len(d) > 0:
        ret['fromColor'] = int(d)
    
    if len(to_parse) == 0:
        return ret

    l, to_parse = to_parse[0], to_parse[1:]
    if l in letter_to_baseblock_guid:
        ret['toBaseBlockGuid'] = letter_to_baseblock_guid[l]
    
    d = ''
    while len(to_parse) > 0 and to_parse[0].isdigit():
        d = d + to_parse[0]
        to_parse = to_parse[1:]
    if len(d) > 0:
        ret['toColor'] = int(d)

    return ret

unknown_blocks = set()
unmappable_blocks = set()
ambiguous_blocks = set()
unknown_meshes = set()

def transform_guid_to_material(input_guid, new_base_block_guid):
    # edge case: transforming a singleton block (base block to base block)
    if input_guid in base_blocks:
        return new_base_block_guid

    # throw an error if the guid isn't real
    if input_guid not in blocks:
        if input_guid not in unknown_blocks:
            logging.warning(f"guid {input_guid} not a known structural block!")
            unknown_blocks.add(input_guid)
        return None
    input_block = blocks[input_guid]

    # find the set of valid mappable blocks by matching mesh
    mesh_guid = mesh_guid_for(input_block)
    if mesh_guid not in by_mesh:
        if mesh_guid not in unknown_meshes:
            logging.warning(f"guid {mesh_guid} not a known mesh!")
            unknown_meshes.add(mesh_guid)
        return None
    valid_remaps = by_mesh[mesh_guid]

    # find a mapped block with the new base block
    output_guids = [k for k, v in valid_remaps.items() if base_block_guid_for(v) == new_base_block_guid]
    if len(output_guids) == 0:
        if (input_guid, new_base_block_guid) not in unmappable_blocks:
            logging.warning(f"guid {input_guid} ({name_for_guid(input_guid)}) can't be mapped to base block {new_base_block_guid} ({name_for_guid(new_base_block_guid)})!")
            unmappable_blocks.add((input_guid, new_base_block_guid))
        return None
    if len(output_guids) > 1:
        if (input_guid, new_base_block_guid) not in ambiguous_blocks:
            logging.warning(f"guid {input_guid} ({name_for_guid(input_guid)}) has ambiguous mapping to base block {new_base_block_guid} ({name_for_guid(new_base_block_guid)}) (candidates: {output_guids})!")
            ambiguous_blocks.add((input_guid, new_base_block_guid))
    return output_guids[0]


def main():
    ap = argparse.ArgumentParser(description="Performs one or more 'refit' operations on structural blocks (mapping one material to another where possible' on an input blueprint, saving the result to an output blueprint.")
    ap.add_argument("input_blueprint", help="The blueprint to mutate.")
    ap.add_argument("output_blueprint", help="The output file name for the blueprint to produce.")
    ap.add_argument("op", nargs="*", help="An operation descriptor (see README).")

    ap.add_argument("-f", action='store_true', help="Allow overwriting of the input blueprint (dangerous!).")

    args = ap.parse_args(sys.argv[1:])

    if args.input_blueprint == args.output_blueprint and not args.f:
        logging.fatal("refusing to overwrite input blueprint (-f to force...)")
        exit(-2)

    with open(args.input_blueprint, mode="r") as input_file:
        blueprint = json.load(input_file)
    
    if "SavedMaterialCost" in blueprint:
        del blueprint["SavedMaterialCost"]
    blueprint["Blueprint"]["ContainedMaterialCost"] = 0.0

    guidToBlockId = {v: int(k) for k, v in blueprint["ItemDictionary"].items()}
    nextBlockId = max(100000, max(guidToBlockId.values()) + 1)

    def block_id_for_guid(guid):
        nonlocal nextBlockId, guidToBlockId
        if guid not in guidToBlockId:
            guidToBlockId[guid] = nextBlockId
            nextBlockId += 1
        return guidToBlockId[guid]
    
    def guid_for_block_id(block_id):
        if str(block_id) in blueprint["ItemDictionary"]:
            return blueprint["ItemDictionary"][str(block_id)]
        candidate_ids = [k for k, v in guidToBlockId.items() if v == block_id]
        if len(candidate_ids) == 0:
            logging.warning(f"no GUID for block id {block_id}!")
            return None
        return candidate_ids[0]

    def apply_op(op, bp, n = 0):
        if op['fromBaseBlockGuid'] is None or op['toBaseBlockGuid'] is None:
            logging.warning("one of the base block guids is unspecified, nothing to do!")
            return
        from_base_block_guid, to_base_block_guid = op['fromBaseBlockGuid'], op['toBaseBlockGuid']

        for sc in bp["SCs"]:
            apply_op(op, sc, n + 1)

        total_updated = 0

        for idx in range(len(bp["BlockIds"])):
            if op['fromColor'] is None or bp["BCI"][idx] == op['fromColor']:
                # dereference the current block
                current_guid  = guid_for_block_id(bp["BlockIds"][idx])
                if current_guid is None:
                    continue

                current_block = block_for_guid(current_guid)
                if current_block is None:
                    continue

                current_base_guid = base_block_guid_for(current_block)

                if current_base_guid == from_base_block_guid:
                    tranformed_guid = transform_guid_to_material(current_guid, to_base_block_guid)
                    if tranformed_guid is not None:
                        new_block_id = block_id_for_guid(tranformed_guid)
                        bp["BlockIds"][idx] = new_block_id
                        if op['toColor'] is not None:
                            bp["BCI"][idx] = op['toColor']
                        total_updated += 1
        
        logging.info(f"{' ' * n}remapped {total_updated} blocks!")

    for op_str in args.op:
        op = parse_op(op_str)
        logging.info(op)
        logging.info(f"mapping {name_for_guid(op['fromBaseBlockGuid'])} to {name_for_guid(op['toBaseBlockGuid'])}...")
        apply_op(op, blueprint["Blueprint"])

    logging.info("updating item dictionary...")

    blueprint["ItemDictionary"] = {str(v): k for k, v in guidToBlockId.items()}
    
    logging.info("saving...")

    with open(args.output_blueprint, mode="w") as output_file:
        json.dump(blueprint, output_file)

    logging.info("all done!")

if __name__ == "__main__":
    main()
