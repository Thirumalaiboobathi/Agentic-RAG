def calculate_bmi(weight: float, height_cm: float):
    height_m = height_cm / 100
    bmi = round(weight / (height_m** 2), 2)
    
    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"

    return {
        "bmi": bmi,
        "category": category
    }
    