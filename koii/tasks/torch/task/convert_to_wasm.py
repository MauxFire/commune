python
import onnx
from onnx2wasm import convert

# Load the ONNX model
onnx_model = onnx.load("model.onnx")

# Convert the ONNX model to WASM
wasm_model = convert(onnx_model)

# Save the WASM model
with open("model.wasm", "wb") as f:
    f.write(wasm_model)

print("ONNX model converted to WASM format.")
