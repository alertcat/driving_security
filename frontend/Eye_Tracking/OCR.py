from paddlex import create_pipeline

pipeline = create_pipeline(pipeline="OCR")
output = pipeline.predict(["test3.jpeg"])
for res in output:
    res.print()
    res.save_to_img("./frontend/des_frontend/Eye_Tracking/assets/alamaan.jpg")
    res.save_to_json("./frontend/des_frontend/Eye_Tracking/output/")