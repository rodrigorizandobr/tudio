
import pytest

def calculate_crop_dimensions(input_w, input_h, target_ratio):
    """
    Simulates the logic in RenderService._create_scene_clip_sync
    to verify resizing and centered cropping.
    """
    if target_ratio == "9:16":
        target_size = (1080, 1920)
        aspect_float = 9/16
    else:
        target_size = (1920, 1080)
        aspect_float = 16/9
        
    input_aspect = input_w / input_h
    
    # 1. Resize logic
    if input_aspect > aspect_float:
        # Input is wider than target => match height
        new_h = target_size[1]
        new_w = int(input_w * (new_h / input_h))
    else:
        # Input is taller/narrower => match width
        new_w = target_size[0]
        new_h = int(input_h * (new_w / input_w))
        
    # 2. Crop logic (centered)
    x1 = new_w / 2 - target_size[0] / 2
    y1 = new_h / 2 - target_size[1] / 2
    
    return {
        "resized_size": (new_w, new_h),
        "crop_coords": (x1, y1, target_size[0], target_size[1])
    }

def test_auto_crop_horizontal():
    # Source: 4:3 (Wider than 9:16, but narrower than 16:9)
    # 1600x1200 -> Input aspect 1.33. Target 16:9 aspect 1.77.
    # input_aspect (1.33) < target_aspect (1.77) => Match Width
    res = calculate_crop_dimensions(1600, 1200, "16:9")
    assert res["resized_size"][0] == 1920
    assert res["resized_size"][1] == 1440 # 1200 * (1920/1600) = 1440
    assert res["crop_coords"][2] == 1920
    assert res["crop_coords"][3] == 1080
    assert res["crop_coords"][1] == (1440 - 1080) / 2 # Centered Y: 180

def test_auto_crop_vertical():
    # Source: 16:9 (Wider than 9:16)
    # 1920x1080 -> Input aspect 1.77. Target 9:16 aspect 0.56.
    # input_aspect (1.77) > target_aspect (0.56) => Match Height
    res = calculate_crop_dimensions(1920, 1080, "9:16")
    assert res["resized_size"][1] == 1920
    assert res["resized_size"][0] == 3413 # 1920 * (1920/1080) = 3413.33 -> 3413
    assert res["crop_coords"][2] == 1080
    assert res["crop_coords"][3] == 1920
    assert res["crop_coords"][0] == (3413 - 1080) / 2 # Centered X: 1166.5

def test_auto_crop_square_to_vertical():
    # Source: 1:1
    res = calculate_crop_dimensions(1000, 1000, "9:16")
    # input_aspect 1.0 > target_aspect 0.56 => Match Height
    assert res["resized_size"][1] == 1920
    assert res["resized_size"][0] == 1920
    assert res["crop_coords"][0] == (1920 - 1080) / 2 # 420

if __name__ == "__main__":
    pytest.main([__file__])
