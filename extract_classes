import yaml
import sqlite3
import os

def extract_classes_from_dataset(dataset_path):
    """Extract class information from YOLOv8 dataset"""
    
    # Find the data.yaml file
    yaml_file = None
    for root, dirs, files in os.walk(dataset_path):
        if 'data.yaml' in files:
            yaml_file = os.path.join(root, 'data.yaml')
            break
    
    if not yaml_file:
        print("❌ Error: data.yaml not found in dataset")
        return None
    
    # Read the YAML file
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)
    
    print(f"✅ Found dataset configuration: {yaml_file}")
    print(f"📁 Dataset path: {data.get('path', 'Not specified')}")
    print(f"🏷️  Number of classes: {data.get('nc', 'Unknown')}")
    print(f"📝 Class names: {data.get('names', 'Not found')}")
    
    return data

def update_database_with_custom_classes(class_data, db_path='eyeknow_objects.db'):
    """Update the database with custom classes"""
    
    if not class_data or 'names' not in class_data:
        print("❌ Error: No class names found in dataset")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing custom objects (keep only COCO classes with ID < 1000)
    cursor.execute('DELETE FROM objects WHERE class_id >= 1000')
    
    # Insert custom classes starting from ID 1000
    custom_objects = []
    class_names = class_data['names']
    
    for i, class_name in enumerate(class_names):
        custom_class_id = 1000 + i  # Start custom classes from 1000
        description = f"Custom object: {class_name}"
        custom_objects.append((custom_class_id, class_name, description))
    
    cursor.executemany('''
        INSERT OR REPLACE INTO objects (class_id, name, description)
        VALUES (?, ?, ?)
    ''', custom_objects)
    
    conn.commit()
    
    # Show what was added
    cursor.execute('SELECT * FROM objects WHERE class_id >= 1000')
    custom_classes = cursor.fetchall()
    
    print(f"\n✅ Added {len(custom_classes)} custom classes to database:")
    for class_info in custom_classes:
        print(f"   ID: {class_info[2]}, Name: {class_info[1]}")
    
    conn.close()
    return custom_classes

def create_class_mapping(dataset_path):
    """Create a mapping file for the custom model"""
    
    # Extract classes
    class_data = extract_classes_from_dataset(dataset_path)
    if not class_data:
        return None
    
    # Update database
    custom_classes = update_database_with_custom_classes(class_data)
    
    # Create mapping file for the model
    mapping = {}
    if 'names' in class_data:
        for i, class_name in enumerate(class_data['names']):
            mapping[i] = {
                'name': class_name,
                'database_id': 1000 + i
            }
    
    # Save mapping to file
    import json
    with open('custom_class_mapping.json', 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"\n✅ Created class mapping file: custom_class_mapping.json")
    
    return mapping, class_data

if __name__ == "__main__":
    # Replace with your actual dataset path
    dataset_path = input("Enter the path to your dataset folder: ").strip()
    
    if not os.path.exists(dataset_path):
        print(f"❌ Error: Dataset path '{dataset_path}' does not exist")
        exit(1)
    
    mapping, class_data = create_class_mapping(dataset_path)
    
    if mapping:
        print(f"\n🎉 Custom dataset integration complete!")
        print(f"📊 Dataset ready for training or using pre-trained model")
        print(f"🗄️  Database updated with {len(mapping)} custom classes")
