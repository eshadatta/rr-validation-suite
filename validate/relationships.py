import json
import os
import re
from csv import DictReader
from validate.utilities import *
import validate.helpers as vh

info = {"file_path": None, "record_info": None, "errors": []}

def rel_pair_validator(label):
    """Setting up the relationship pairs for relationship types"""

    p = "Parent"
    c = "Child"
    r = "Related"
    pair = {p: c, c: p, r: r}
    return pair.get(label, None)


def rel_values_mapping():
    """Setting up the relationship pairs for institution names"""
    return {"label": "name", "id": "id"}

def validate_relationship(file_rel, related_rel):
    err = {}
    err[related_rel['id']] = []
    paired_value = rel_pair_validator(file_rel['type'])

    # Relationship type occur in pairs, they must equal the paired controlled vocabulary
    if not (paired_value == related_rel['related_relationship']['type']):
        err[related_rel['id']].append(f"Illegal relationship pairing: relationship type: {related_rel['related_relationship']['type']} should be {paired_value}")

    # Names of related institutions must equal each other
    mappings = rel_values_mapping()
    for k, v in mappings.items():
        if not (file_rel[k] == related_rel[v]) or not (
                related_rel['related_relationship'][k]
                == info['record_info'][v]):
            err[related_rel['id']].append(f"Values are not equal: validating record: {info['record_info'][v]} and relationship: {file_rel} and related record: {related_rel}")
    if err[related_rel['id']]:
        info["errors"].append(err)


def generate_related_relationships(id, name, rel):
    record = {}
    record['id'] = id
    record['name'] = name
    if len(rel) > 0:
        record['related_relationship'] = list(
            filter(lambda d: d['id'] == info["record_info"]["id"], rel))
    if (len(rel) == 0) or (len(record['related_relationship']) == 0):
        record['related_relationship'] = None
    else:
        record['related_relationship'] = record['related_relationship'][0]
    return record


def get_related_records(record_id):
    related_record = {}
    filename = info["file_path"] + "/" + record_id.split(
        "ror.org/")[1] + ".json"
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            related_record = generate_related_relationships(
                data['id'], data['name'], data['relationships'])
        except Exception as e:
            raise RuntimeError (f"Couldn't open file {filename}: {e}")
    return related_record

def parse_record_id(id):
    parsed_id = None
    pattern = '^https:\/\/ror.org\/(0[a-x|0-9]{8})$'
    ror_id = re.search(pattern, id)
    if ror_id:
        parsed_id = ror_id.group(1)
    else:
        info["errors"].append(f"ROR ID: {id} does not match format: {pattern}. Record will not be validated")
    return parsed_id

def read_relationship_from_file(rel_file):
    relation = []
    rel_dict = {}
    try:
        with open(rel_file, 'r') as rel:
            relationships = DictReader(rel)
            for row in relationships:
                check_record_id = parse_record_id(row['Record ID'])
                check_related_id = parse_record_id(row['Related ID'])
                if (check_record_id and check_related_id): 
                    rel_dict['short_record_id'] = check_record_id
                    rel_dict['short_related_id'] = check_related_id
                    rel_dict['record_id'] = row['Record ID']
                    rel_dict['related_id'] = row['Related ID']
                    rel_dict['record_relationship'] = row['Relationship of Related ID to Record ID']
                    relation.append(rel_dict.copy())
    except IOError as e:
        raise RuntimeError(f"Reading file {rel_file}: {e}")
    return relation

def get_single_related_relationship(related_id):
    return get_related_records(related_id)

def check_relationships_from_file(current_record, file_path, rel_file):
    files_exist = []
    chk_relshp = read_relationship_from_file(rel_file)
    get_file_ids = list(i['record_id'] for i in chk_relshp)
    if current_record['id'] in get_file_ids:
        rel = vh.get_relationship_info()
        if rel['rel']:
            info["file_path"] = file_path
            info["record_info"] = rel
            info["errors"] = []
            all_current_id_relationships = list(i for i in chk_relshp if i['record_id'] == current_record['id'])
            for r in all_current_id_relationships:
                file_rel = list(rel for rel in current_record['relationships'] if rel['id'] == r['related_id'])
                file_rel = file_rel[0]
                related_relshp = get_related_records(r['related_id'])
                if related_relshp:
                    files_exist.append(r['related_id'])
                    if related_relshp['related_relationship']:
                        validate_relationship(file_rel, related_relshp)
                    else:
                        info["errors"].append(
                        f"Related relationship not found for {related_relshp['id']}")
            if len(files_exist) == 0:
                info["errors"].append(f"According to {rel_file}, relationships exist for {current_record['id']}. At least one file listed in relationships must exist")  
        else:
            info["errors"].append(f"According to {rel_file}, relationships exist for {current_record['id']}. However, no relationships exist in the file")  

  
    return info["errors"]

def check_relationships():
    files_exist = []
    for record in info['record_info']['rel']:
        related_relshp = get_related_records(record['id'])
        print(related_relshp)
        if related_relshp:
            files_exist.append(record['id'])
            if related_relshp['related_relationship']:
                validate_relationship(record, related_relshp)
            else:
                info["errors"].append(
                    f"Related relationship not found for {related_relshp['id']}")
    if len(files_exist) == 0:
        info["errors"].append(f"Relationships exist for {info['record_info']['id']}. At least one file listed in relationships must exist")    
    return info["errors"]

def process_relationships(current_record, file_path, rel_file=None):
    msg = None
    if rel_file:
        msg = check_relationships_from_file(current_record, file_path, rel_file)
    else:
        rel = vh.get_relationship_info()
        if rel['rel']:
            info["file_path"] = file_path
            info["record_info"] = rel
            info["errors"] = []
            msg = check_relationships()
        else:
            msg = "No relationships found, nothing to check"
    return msg
    