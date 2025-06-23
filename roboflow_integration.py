"""
Roboflow Dataset Integration for EyeKnow
This script helps integrate your Roboflow dataset with the EyeKnow system
"""

import os
import yaml
import json
import shutil
from pathlib import Path

def find_roboflow_dataset():
    """Find the Roboflow dataset in common locations"""
    
    possible_paths = [
        "/home/sia2/EyeKnow/roboflow_dataset/eyeknow-11",
        "./roboflow_dataset/eyeknow-11", 
        "./eyeknow-11",
        "."
    ]
    
    for base_path in possible_paths:
        data_yaml = os.path.join(base_path, "data.yaml")
        if os.path.exists(data_yaml):
            return base_path, data_yaml
    
    return None, None

def download_roboflow_dataset(api_key="43AtcCwlHX4PUSf5Nl6O"):
    """Download dataset from Roboflow if not present"""
    
    print("📦 Downloading dataset from Roboflow...")
    
    try:
        from roboflow import Roboflow
        
        rf = Roboflow(api_key=api_key)
        project = rf.workspace("eyeknow").project("eyeknow")
        version = project.version(11)
        dataset = version.download("yolov8")
        
        print(f"✅ Dataset downloaded to: {dataset.location}")
        return dataset.location
        
    except ImportError:
        print("❌ Roboflow package not installed. Install with: pip install roboflow")
        return None
    except Exception as e:
        print(f"❌ Error downloading dataset: {e}")
        return None

def setup_roboflow_integration():
    """Complete setup of Roboflow integration"""
    
    print("🔄 Setting up Roboflow integration...")
    
    # 1. Find existing dataset
    dataset_path, data_yaml = find_roboflow_dataset()
    
    if not dataset_path:
        print("📥 Dataset not found locally. Attempting download...")
        dataset_path = download_roboflow_dataset()
        
        if dataset_path:
            data_yaml = os.path.join(dataset_path, "data.yaml")
        else:
            print("❌ Could not find or download dataset")
            return False
    
    print(f"📊 Using dataset: {dataset_path}")
    
    # 2. Read dataset configuration
    try:
        with open(data_yaml, 'r') as f:
            data = yaml.safe_load(f)
        
        print(f"✅ Dataset info:")
        print(f"   Path: {data.get('path', 'Not specified')}")
        print(f"   Classes: {data.get('nc', 'Unknown')}")
        print(f"   Names: {data.get('names', 'Not found')}")
        
    except Exception as e:
        print(f"❌ Error reading dataset config: {e}")
        return False
    
    # 3. Update database with custom classes
    try:
        import setup_database
        setup_database.create_database()
        print("✅ Database updated with dataset classes")
    except Exception as e:
        print(f"❌ Database update failed: {e}")
        return False
    
    # 4. Check for trained model
    model_locations = [
        os.path.join(dataset_path, "runs/detect/train/weights/best.pt"),
        os.path.join(dataset_path, "best.pt"),
        "./eyeknow_custom_model.pt",
        "./best.pt"
    ]
    
    custom_model = None
    for model_path in model_locations:
        if os.path.exists(model_path):
            custom_model = model_path
            break
    
    if custom_model:
        # Copy to standard location
        shutil.copy2(custom_model, "./eyeknow_custom_model.pt")
        print(f"✅ Found custom model: {custom_model}")
        print("✅ Copied to: ./eyeknow_custom_model.pt")
    else:
        print("⚠️ No trained model found. You can:")
        print("   1. Train with: python quick_train.py")
        print("   2. Use pretrained YOLOv8 for now")
    
    # 5. Update quick_train.py with correct dataset path
    update_training_script(data_yaml)
    
    print("\n🎉 Roboflow integration setup complete!")
    return True

def update_training_script(data_yaml_path):
    """Update quick_train.py with the correct dataset path"""
    
    try:
        # Read current quick_train.py
        if os.path.exists("quick_train.py"):
            with open("quick_train.py", 'r') as f:
                content = f.read()
            
            # Update dataset path
            old_path = 'dataset_path = "/home/sia2/EyeKnow/roboflow_dataset/eyeknow-11/data.yaml"'
            new_path = f'dataset_path = "{data_yaml_path}"'
            
            updated_content = content.replace(old_path, new_path)
            
            # Write back
            with open("quick_train.py", 'w') as f:
                f.write(updated_content)
            
            print(f"✅ Updated quick_train.py with dataset path: {data_yaml_path}")
        
    except Exception as e:
        print(f"⚠️ Could not update quick_train.py: {e}")

def check_dataset_status():
    """Check the current status of the dataset integration"""
    
    print("📋 EyeKnow Dataset Status")
    print("=" * 50)
    
    # Check dataset
    dataset_path, data_yaml = find_roboflow_dataset()
    if dataset_path:
        print(f"✅ Dataset found: {dataset_path}")
        
        try:
            with open(data_yaml, 'r') as f:
                data = yaml.safe_load(f)
            
            print(f"📊 Classes: {data.get('nc', 'Unknown')}")
            if 'names' in data:
                print("📝 Object classes:")
                for i, name in enumerate(data['names']):
                    print(f"   {i}: {name}")
        except:
            print("⚠️ Could not read dataset details")
    else:
        print("❌ Dataset not found")
    
    # Check database
    if os.path.exists("eyeknow_objects.db"):
        print("✅ Database exists")
        
        try:
            import sqlite3
            conn = sqlite3.connect("eyeknow_objects.db")
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM objects WHERE class_id >= 1000")
            custom_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM objects")
            total_count = cursor.fetchone()[0]
            
            print(f"📊 Database: {total_count} total objects, {custom_count} custom")
            
            if custom_count > 0:
                cursor.execute("SELECT class_id, name FROM objects WHERE class_id >= 1000 LIMIT 5")
                objects = cursor.fetchall()
                print("📝 Sample custom objects:")
                for obj in objects:
                    print(f"   {obj[0]}: {obj[1]}")
            
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Database query failed: {e}")
    else:
        print("❌ Database not found")
    
    # Check model
    model_files = [
        "eyeknow_custom_model.pt",
        "eyeknow_quick_model.pt", 
        "best.pt"
    ]
    
    model_found = False
    for model_file in model_files:
        if os.path.exists(model_file):
            print(f"✅ Model found: {model_file}")
            model_found = True
            break
    
    if not model_found:
        print("⚠️ No custom model found")
    
    # Check mapping
    if os.path.exists("custom_class_mapping.json"):
        print("✅ Class mapping file exists")
        try:
            with open("custom_class_mapping.json", 'r') as f:
                mapping = json.load(f)
            print(f"📊 Mapping: {len(mapping)} classes")
        except:
            print("⚠️ Could not read mapping file")
    else:
        print("⚠️ Class mapping file not found")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Roboflow Integration for EyeKnow')
    parser.add_argument('--setup', action='store_true', help='Setup Roboflow integration')
    parser.add_argument('--status', action='store_true', help='Check integration status')
    parser.add_argument('--download', action='store_true', help='Download dataset from Roboflow')
    
    args = parser.parse_args()
    
    if args.setup:
        setup_roboflow_integration()
    elif args.status:
        check_dataset_status()
    elif args.download:
        download_roboflow_dataset()
    else:
        print("EyeKnow Roboflow Integration")
        print("Usage:")
        print("  python roboflow_integration.py --setup    # Setup integration")
        print("  python roboflow_integration.py --status   # Check status")
        print("  python roboflow_integration.py --download # Download dataset")
