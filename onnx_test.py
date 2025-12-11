import onnxruntime as ort

path = r"C:\Users\14685\Desktop\PackageWizard1.1\model\yolo_model\pin_detect\BGA_pin_detect.onnx"
try:
    sess = ort.InferenceSession(path)
    print("onnxruntime 加载成功")
except Exception as e:
    print("onnxruntime 加载错误：", repr(e))
