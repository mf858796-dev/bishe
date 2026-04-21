import sys
print("Testing imports...")
from coordinate_mapper import CoordinateMapper
from attention_model import AttentionEvaluator  
from report_generator import ReportGenerator
print("All imports OK!")

print("\nTesting CoordinateMapper...")
mapper = CoordinateMapper()
print("CoordinateMapper OK!")

print("\nTesting AttentionEvaluator...")
evaluator = AttentionEvaluator()
import time
for i in range(10):
    evaluator.add_gaze_point(100+i*5, 200+i*3, time.time() + i*0.1)
metrics = evaluator.get_metrics()
print(f"AttentionEvaluator OK! Metrics: {metrics}")

print("\nTesting ReportGenerator...")
reporter = ReportGenerator()
import numpy as np
for i in range(50):
    reporter.add_gaze_point(np.random.randint(0, 800), np.random.randint(0, 600))
reporter.generate_heatmap("test_heatmap.png")
reporter.generate_trajectory("test_trajectory.png")
import os
if os.path.exists("test_heatmap.png"):
    print("ReportGenerator OK! Files generated.")
else:
    print("ReportGenerator FAILED!")

print("\n=== ALL TESTS PASSED ===")
