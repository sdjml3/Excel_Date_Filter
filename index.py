from flask import Flask,send_file, render_template, request, redirect, url_for, jsonify, send_file
from datetime import datetime
import pandas as pd
import os,io






app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists('uploads'):
    os.makedirs('uploads')

FILE_PATH = None


@app.route("/", methods=["GET", "POST"])
def index():
    global FILE_PATH

    if request.method == "POST":
        file = request.files.get("file")

        if not file:
            return "No file selected."

        if not file.filename.endswith((".xlsx", ".xls")):
            return "Upload only Excel files."

        FILE_PATH = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(FILE_PATH)

        return redirect(url_for("index"))

    data = []
    columns = []
    message = ""

    if FILE_PATH:

        # Read Excel
        df = pd.read_excel(FILE_PATH)

        if df.empty:
            message = "Excel file is empty."
        else:
            try:
                time_column = df.columns[0]

                df_long = df.melt(
                    id_vars=[time_column],
                    var_name="Date",
                    value_name="Value"
                )

                df_long["Date and Time"] = pd.to_datetime(
                    df_long["Date"].astype(str) + " " +
                    df_long[time_column].astype(str),
                    errors="coerce"
                )

                df_long = df_long.dropna(subset=["Date and Time"])

                from_date = request.args.get("from_date")
                from_hour = request.args.get("from_hour")
                to_date = request.args.get("to_date")
                to_hour = request.args.get("to_hour")

                if from_date:
                    from_hour = int(from_hour) if from_hour else 0
                    from_dt = pd.to_datetime(from_date) + pd.Timedelta(hours=from_hour)
                    df_long = df_long[df_long["Date and Time"] >= from_dt]

                if to_date:
                    to_hour = int(to_hour) if to_hour else 23
                    to_dt = pd.to_datetime(to_date) + pd.Timedelta(hours=to_hour)
                    df_long = df_long[df_long["Date and Time"] <= to_dt]


                df_long["Date and Time"] = df_long["Date and Time"].dt.strftime('%d-%m-%Y %H')


                result_df = df_long[["Date and Time", "Value"]]

                columns = result_df.columns.tolist()
                data = result_df.to_dict(orient="records")

            except Exception as e:
                message = f"Error processing file: {str(e)}"

    return render_template(
        "index.html",
        data=data,
        columns=columns,
        message=message
    )




@app.route("/save_history", methods=["GET","POST"])
def save_history():

    data = request.json

    from_date = data.get("from_date")
    to_date = data.get("to_date")
    from_time = data.get("from_time") 
    to_time = data.get("to_time")

    if not all([from_date, to_date]):
        return jsonify({"status": "error", "message": "All fields required"}), 400


    try:
        datetime.strptime(from_date, "%d-%m-%Y")
        datetime.strptime(to_date, "%d-%m-%Y")
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format"}), 400


    try:
        if from_time=="":
            from_time="--"
        elif from_time!="":
            from_time=int(from_time)
            from_time=f"{from_time:02d}"            
        if to_time=="":
            to_time="--"
        elif to_time!="":
            to_time=int(to_time)
            to_time=f"{to_time:02d}"

    except ValueError:
        return jsonify({"status": "error", "message": "Invalid hour"}), 400

    entry = f"From: {from_date} {from_time} | To: {to_date} {to_time}"

    file_path = "uploads/history.txt"

    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            lines = file.readlines()

    if len(lines) >= 5:
        lines = lines[1:]   


    lines.append(entry + "\n")


    with open(file_path, "w") as file:
        file.writelines(lines)

    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            lines = file.readlines()

            lines = [line.strip() for line in lines if line.strip()]
            print(lines)
               
    return render_template("index.html",lines=lines)


@app.route("/get_history", methods=["GET"])
def get_history():

    file_path = "uploads/history.txt"

    if not os.path.exists(file_path):
        return jsonify({"history": []})

    with open(file_path, "r") as file:
        lines = file.readlines()
    lines.reverse()

    clean_lines = [line.strip() for line in lines if line.strip()]

    return jsonify({"history": clean_lines})


if __name__ == "__main__":
    app.run(debug=True)
