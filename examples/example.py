from dicom_insight import analyze_path

# Replace with your file/folder.
report = analyze_path("./sample-study")
print(report.summary)
print(report.to_json())
