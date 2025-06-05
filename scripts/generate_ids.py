#!/usr/bin/env python


import sys
import click
import hashlib
import logging
import re
import yaml

from collections import defaultdict, deque
from typing import  Optional, Set, List, Dict, Any
from uuid import uuid4

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)



class IdentifierGenerator:
    def __init__(
        self, namespace: str, type_prefix: Optional[str] = None,
    ):
        self.namespace = namespace
        self.type_prefix = type_prefix
        self.registered_ids: Set[str] = set()

    def is_id_available(self, identifier: str) -> bool:
        if identifier in self.registered_ids:
            return False

        return True

    def is_namespace_id(self, key: str):
        if key.startswith(self.namespace):
            return True
        return False
    
    def is_valid_id(self, key: str, method: str = "hash") -> bool:
        # Check if key starts with namespace
        if not key.startswith(self.namespace):
            return False
        
        # Remove namespace to get the remaining part
        remaining = key[len(self.namespace):]
        
        # Define expected unique part patterns based on method
        if method == "uuid":
            unique_pattern = r'^[0-9a-f]{8}$'  # 8 hex chars
        elif method == "hash":
            unique_pattern = r'^[0-9a-f]{10}$'  # 10 hex chars
        else:
            raise NotImplementedError
        
        # Check pattern based on whether type_prefix is used
        if self.type_prefix is not None:
            # Expected format: {type_prefix}-{unique_part}
            expected_prefix = f"{self.type_prefix}-"
            if not remaining.startswith(expected_prefix):
                return False
            # Extract unique part after type_prefix and dash
            unique_part = remaining[len(expected_prefix):]
        else:
            # Expected format: {unique_part} directly
            unique_part = remaining
        
        # Validate the unique part matches the expected pattern
        return bool(re.match(unique_pattern, unique_part))

    def register_id(self, identifier: str) -> None:
        self.registered_ids.add(identifier)

    def generate_id(
        self,
        term_name: str,
        method: str = "hash",
        check_collision: bool = True,
        max_attempts: int = 10,
    ) -> str:
        """
        Generate a structured identifier for a vocabulary term with collision detection.

        Args:
            term_name: The name of the term
            method: ID generation method ('uuid', 'hash', 'sequential', or 'slug')
            check_collision: Whether to check for collisions
            max_attempts: Maximum number of attempts to generate a unique ID

        Returns:
            A structured identifier that's unique and available
        """
        attempts = 0

        while attempts < max_attempts:
            # Generate unique part based on method
            if method == "uuid":
                unique_part = str(uuid4())[:8]  # First 8 chars of UUID

            elif method == "hash":
                # Create a hash of the term name, possibly with a salt for retry attempts
                if attempts > 0:
                    salted_name = f"{term_name}-attempt-{attempts}"
                else:
                    salted_name = term_name

                hash_obj = hashlib.md5(salted_name.encode())
                unique_part = hash_obj.hexdigest()[:10]

            else:
                raise ValueError(
                    f"Unknown method: {method}. Available methods: uuid, hash, sequential, slug"
                )

            # Construct the full identifier
            if self.type_prefix is None:
                identifier = f"{self.namespace}{unique_part}"
            else:
                identifier = f"{self.namespace}{self.type_prefix}-{unique_part}"

            # Check if this identifier is available
            if check_collision:
                if self.is_id_available(identifier):
                    # Register the ID as used
                    self.register_id(identifier)
                    return identifier
            else:
                return identifier

            # If we got here, there was a collision - try again
            attempts += 1

        # If we exhausted all attempts, raise an error
        raise RuntimeError(
            f"Could not generate a unique identifier for '{term_name}' after {max_attempts} attempts"
        )


def topological_sort(objects: List[Dict], id_key: str, parent_key: str, id_generator: IdentifierGenerator) -> List[Dict]:
    if parent_key is None:
        return objects
    logger.debug("Performing topological sort")
    # Build adjacency list and in-degree map
    adj_list = defaultdict(list)
    in_degree = defaultdict(int)
    obj_map = {obj.get(id_key, None): obj for obj in objects}

    for obj in objects:
        parent = obj.get(parent_key, None)
        if parent is not None:
            if not id_generator.is_valid_id(parent):
                adj_list[parent].append(obj.get(id_key, None))
                in_degree[obj.get(id_key, None)] += 1

    # Collect nodes with no incoming edges (in-degree 0)
    queue = deque()
    for obj_id in obj_map:
        if in_degree[obj_id] == 0:
            queue.append(obj_id)

    # Perform topological sort
    sorted_ids = []
    while queue:
        current = queue.popleft()
        sorted_ids.append(current)

        for child in adj_list[current]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    # Return sorted objects
    return [obj_map[obj_id] for obj_id in sorted_ids]


def check_uniqueness(data: List[Dict[str, Any]], key: str) -> bool:
    """
    Check if all values for a given key are unique and not None.
    
    Args:
        data: List of dictionaries containing the data
        key: The key to check for uniqueness
        
    Returns:
        True if all values are unique and not None, False otherwise
    """
    values = []
    for item in data:
        value = item.get(key)
        if value is None:
            logger.error(f"Found None value for key '{key}' in item: {item}")
            return False
        values.append(value)
    
    # Check for duplicates
    unique_values = set(values)
    if len(unique_values) != len(values):
        duplicates = [v for v in values if values.count(v) > 1]
        logger.error(f"Found duplicate values for key '{key}': {set(duplicates)}")
        return False
    
    return True


@click.command()
@click.option(
    "--data",
    "-d",
    "data_path",
    required=True,
    type=click.Path(exists=True),
    help="Path to the YAML data file",
)
@click.option(
    "--target",
    "-t",
    "target_name",
    required=True,
    help="Name of the target entity list in the data file",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    required=False,
    type=click.Path(),
    help="Path to output YAML data file (defaults to input file)",
    default=None,
)
@click.option(
    "--type-prefix",
    "type_prefix",
    required=False,
    type=str,
    default=None,
    help="Vocabulary-specific prefix for uri to be generated.",
)
@click.option(
    "--preflabel",
    "preflabel",
    required=True,
    type=str,
    help="Key to human readable identifier field for resource.",
)
@click.option(
    "--namespace",
    "namespace",
    required=True,
    type=str,
    help="Namespace prefix used to create identifiers for the vocabulary.",
)
@click.option(
    "--id-key",
    "id_key",
    required=False,
    type=str,
    default="id",
    help="Key to machine readable identifier field for resource.",
)
@click.option(
    "--method",
    "method",
    required=False,
    type=click.Choice(['uuid', 'hash']),
    default="hash",
    help="ID generation method.",
)
@click.option(
    "--parent-key",
    "parent_key",
    required=False,
    type=str,
    default=None,
    help="Field name for parent of same type.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be changed without writing files",
)
def generate_id(
    data_path: str,
    target_name: str,
    preflabel: str,
    namespace: str,
    verbose: bool = False,
    output_path: str = None,
    type_prefix: str = None,
    id_key: str = "id",
    method: str = "hash",
    dry_run: bool = False,
    parent_key: str = None
):
    """
    Generate identifiers for all vocabulary terms and return an updated file.
    """
    # Set logging level based on verbose flag
    if verbose:
        logger.setLevel(logging.DEBUG)

    try:
        # Load YAML data
        logger.info(f"Loading data from: {data_path}")
        with open(data_path, 'r', encoding='utf-8') as f:
            yaml_root = yaml.safe_load(f)
        
        # Extract target entities
        if target_name not in yaml_root:
            raise ValueError(f"Target '{target_name}' not found in YAML file. Available keys: {list(yaml_root.keys())}")
        
        entities = yaml_root[target_name]
        if not isinstance(entities, list):
            raise ValueError(f"Target '{target_name}' is not a list")
        
        id_generator = IdentifierGenerator(namespace=namespace, type_prefix=type_prefix)
        num_entities_presort = len(entities)
        if parent_key is not None:
            entities = topological_sort(entities, id_key, parent_key, id_generator)
            num_entities_postsort = len(entities)
            if num_entities_postsort != num_entities_presort:
                logger.error("Error when performing topological sort. Not the same number of entities pre and post sorting.")
                sys.exit(1)

        logger.info(f"Found {len(entities)} entities in '{target_name}'")

        # Check uniqueness of preflabels before processing
        logger.info(f"Checking uniqueness of '{preflabel}' values...")
        if not check_uniqueness(entities, preflabel):
            raise ValueError(f"Preflabel field '{preflabel}' contains non-unique or None values")
        
        new_ids_generated = 0
        updated_entities = 0
        id_map = dict()

        # Process entities
        for i, entity in enumerate(entities):
            if not isinstance(entity, dict):
                logger.warning(f"Skipping non-dict entity at index {i}: {entity}")
                sys.exit(1)
            
            # Check current ID
            current_id = entity.get(id_key)
            
            if current_id and id_generator.is_valid_id(current_id, method=method):
                # Valid existing ID - register it to prevent collisions
                id_generator.register_id(current_id)
                logger.debug(f"Registered existing valid ID: {current_id}")
            else:
                # Generate new ID
                preflabel_value = entity.get(preflabel)
                if not preflabel_value:
                    logger.error(f"Entity at index {i} has no value for preflabel '{preflabel}': {entity}")
                    sys.exit(1)
                
                old_id = entity[id_key]
                new_id = id_generator.generate_id(preflabel_value, method=method)
                id_map[old_id] = new_id
                entity[id_key] = new_id
                logger.debug(f"Generated new ID for '{preflabel_value}': {new_id}")
                new_ids_generated += 1
                updated_entities += 1
                
            if parent_key is not None:
                old_parent_id = entity.get(parent_key, None)
                if old_parent_id is not None:
                    if not id_generator.is_valid_id(old_parent_id, method=method):
                        new_parent_id = id_map[old_parent_id]
                        entity[parent_key] = new_parent_id
                
        
        # Final uniqueness check for all IDs
        logger.info("Performing final uniqueness check for all IDs...")
        if not check_uniqueness(entities, id_key):
            raise ValueError(f"ID field '{id_key}' contains non-unique values after processing")
        
        # Report results
        logger.info("Processing complete:")
        logger.info(f"  - Total entities: {len(entities)}")
        logger.info(f"  - New IDs generated: {new_ids_generated}")
        logger.info(f"  - Entities updated: {updated_entities}")
        
        # Write output file
        if not dry_run:
            if output_path is None:
                output_path = data_path
            
            logger.info(f"Writing updated data to: {output_path}")
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(yaml_root, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            logger.info(f"Successfully wrote updated YAML file: {output_path}")
        else:
            logger.info("Dry run complete - no files were modified")

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    generate_id()
