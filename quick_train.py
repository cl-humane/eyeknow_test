from ultralytics import YOLO
import time
import os

print("⚡ Quick EyeKnow Training (Fixed)")
print("📊 Optimized for 1,400 image dataset")

# Load model
model = YOLO('yolov8n.pt')

# Use your existing dataset but with speed optimizations
dataset_path = "/home/sia2/EyeKnow/roboflow_dataset/eyeknow-11/data.yaml"

# Check dataset exists
if not os.path.exists(dataset_path):
    print(f"❌ Error: Dataset not found at {dataset_path}")
    exit(1)

print("⚙️ Speed-optimized settings:")
print("   - Epochs: 8 (vs original 50)")
print("   - Image size: 320 (vs original 640)")
print("   - All speed optimizations enabled")

start_time = time.time()

try:
    results = model.train(
        data=dataset_path,
        epochs=8,           # Reduced from 50
        imgsz=320,         # Reduced from 640
        batch=1,           # Pi optimized
        device='cpu',
        workers=0,         # No multiprocessing
        cache=False,       # Don't cache (saves RAM)
        amp=False,         # Disable mixed precision
        plots=False,       # Skip plots (saves time)
        save_period=-1,    # Don't save intermediate
        patience=4,        # Early stopping
        project='quick_training',
        name='fast_run',
        exist_ok=True,
        verbose=True
    )
    
    elapsed = time.time() - start_time
    print(f"\n🎉 Training completed in {elapsed/60:.1f} minutes!")
    
    # Copy model
    import shutil
    best_model = results.save_dir / 'weights' / 'best.pt'
    shutil.copy(best_model, '/home/sia2/EyeKnow/eyeknow_quick_model.pt')
    print("✅ Quick model saved!")
    
except Exception as e:
    print(f"❌ Training failed: {e}")
