python
import torch
import torch.nn as nn
import torch.onnx

# Define a simple model
class SimpleModel(nn.Module):
    def __init__(self):
        super(SimpleModel, self).__init__()
        self.fc = nn.Linear(10, 1)

    def forward(self, x):
        return self.fc(x)

# Create an instance of the model
model = SimpleModel()

# Create a dummy input
dummy_input = torch.randn(1, 10)

# Export the model to ONNX format
torch.onnx.export(model, dummy_input, "model.onnx", verbose=True)

print("PyTorch model exported to ONNX format.")
