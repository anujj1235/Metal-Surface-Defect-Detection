import tensorflow as tf
from pathlib import Path

MODEL_PATH = Path("model/metal_defect_resnet50.keras")

print("=" * 70)
print("LOADING MODEL")
print("=" * 70)

model = tf.keras.models.load_model(
    str(MODEL_PATH),
    compile=False
)

print()
print("MODEL TYPE:")
print(type(model))

print()
print("MODEL NAME:")
print(model.name)

print()
print("MODEL INPUT:")
print(model.input)

print()
print("MODEL OUTPUT:")
print(model.output)

print()
print("INPUT SHAPE:")
print(model.input_shape)

print()
print("OUTPUT SHAPE:")
print(model.output_shape)

print()
print("=" * 70)
print("MODEL LAYERS")
print("=" * 70)

for i, layer in enumerate(model.layers):
    print(
        f"{i:3d} | "
        f"{layer.name:35s} | "
        f"{type(layer).__name__:25s} | "
        f"input={getattr(layer, 'input_shape', 'N/A')} | "
        f"output={getattr(layer, 'output_shape', 'N/A')}"
    )

    if isinstance(layer, tf.keras.Model):
        print("      ---- NESTED MODEL ----")

        for j, sub_layer in enumerate(layer.layers):
            print(
                f"      {j:3d} | "
                f"{sub_layer.name:35s} | "
                f"{type(sub_layer).__name__:25s}"
            )

print()
print("=" * 70)
print("DIRECT MODEL TEST")
print("=" * 70)

import numpy as np

x = np.zeros(
    (1, 224, 224, 3),
    dtype=np.float32
)

try:

    y = model(
        tf.convert_to_tensor(x),
        training=False
    )

    print("DIRECT MODEL CALL: SUCCESS")
    print("OUTPUT:")
    print(y)

except Exception as e:

    print("DIRECT MODEL CALL: FAILED")
    print(type(e).__name__)
    print(str(e))

print()
print("=" * 70)
print("END")
print("=" * 70)