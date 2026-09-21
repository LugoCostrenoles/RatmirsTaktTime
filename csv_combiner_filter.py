import pandas as pd
import glob
import os
import sys
import tkinter as tk
import re
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np
from tkinter import Toplevel, ttk
from PIL import Image, ImageTk
import tkinter.font as tkfont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def export_pdf(data, filename, header="Taktzeit Auswertung App", subheader="", time_span=None):
    styles = getSampleStyleSheet()

    def wrap_cells(data):
        # Assume header row first, the rest data rows
        wrapped_data = [data[0]]  # keep the headers as is
        for row in data[1:]:
            # Wrap first column (dataset name) in a Paragraph
            new_row = [Paragraph(str(row[0]), styles['Normal'])] + list(row[1:])
            wrapped_data.append(new_row)
        return wrapped_data
    pdf = SimpleDocTemplate(filename, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    flowables = []
    # Header and subheader
    flowables.append(Paragraph(f"<b>{header}</b>", styles['Title']))
    if subheader:
        flowables.append(Spacer(1, 10))
        flowables.append(Paragraph(f"<b>{subheader}</b>", styles['Heading2']))
    if time_span:
        flowables.append(Spacer(1, 10))
        flowables.append(Paragraph(time_span, styles['Normal']))
    flowables.append(Spacer(1, 16))
    
    
    PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
    LEFT_MARGIN = RIGHT_MARGIN = 20  # As set in your SimpleDocTemplate
    usable_width = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

    ncols = len(data[0])
    col_width = usable_width / ncols
    
    table_data = wrap_cells(data)  # wrap your data before passing to Table()
    tbl = Table(table_data, repeatRows=1, colWidths=[col_width]*ncols)    
    tbl_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1, 0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ])
    tbl.setStyle(tbl_style)
    flowables.append(tbl)
    pdf.build(flowables) 

def load_naming_dict(path="naming.csv"):
    try:
        df_name = pd.read_csv(path, header=None, names=["key", "suffix"], encoding="latin1", delimiter=';')
        return dict(zip(df_name["key"], df_name["suffix"]))
    except Exception as e:
        print(f"Warnung: Konnte naming.csv nicht laden: {e}")
        messagebox.showwarning("Warnung", f"Konnte naming.csv nicht laden: {e}")
        return {}

NAMING_DICT = load_naming_dict(os.path.join(os.path.dirname(__file__), "naming.csv"))

                                                            # --- COMBINE AND FILTER CSV FILES IN THE FOLDER --- #
def combine_and_filter_csvs(folder_path):
    output_file = os.path.join(folder_path, 'kombiniert_gefiltert.csv')
    all_csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
    csv_files = [f for f in all_csv_files if os.path.abspath(f) not in (
        os.path.abspath(os.path.join(folder_path, 'kombiniert_output.csv')),
        os.path.abspath(output_file)
    )]

    if not csv_files:
        messagebox.showerror("Fehler", f"Im Ordner wurden keine CSV-Dateien gefunden:\n{folder_path}")
        return

    dfs = []
    for file in csv_files:
        df = pd.read_csv(file, delimiter=';',low_memory=False)
        if df.shape[1] != 2:
            messagebox.showwarning(
                "Falsches Format",
                f"Die Datei '{os.path.basename(file)}' hat nicht genau 2 Spalten und wird übersprungen."
            )
            continue

        filename = os.path.splitext(os.path.basename(file))[0]
        date_time_split = df.iloc[:, 0].str.split(',', n=1, expand=True)
        date_part = date_time_split[0].str.strip()
        time_part = date_time_split[1].str.strip()

        # Filter rows where time is between 04:55:00 and 21:55:00 inclusive:
        mask = time_part.between("04:55:00", "21:55:00")
        filtered_df = pd.DataFrame({
            "Datum": date_part[mask].reset_index(drop=True),
            "Uhrzeit": time_part[mask].reset_index(drop=True),
            filename: df.iloc[:, 1][mask].reset_index(drop=True)
        })

        if not filtered_df.empty:
            dfs.append(filtered_df)

    if not dfs:
        messagebox.showerror("Fehler", "Es wurden keine gültigen CSV-Dateien gefunden oder keine Zeilen entsprachen dem Zeitfilter.")
        return

    # Concatenate horizontally—blocks may differ in length
    combined_df = pd.concat(dfs, axis=1)

    try:
        combined_df.to_csv(output_file, index=False, sep=';')
        messagebox.showinfo("Erfolg", f"Gefilterte kombinierte CSV-Datei gespeichert als:\n{output_file}")
        # Enable the "Show stats" button now
        show_stats_btn.config(state="normal")
    except PermissionError:
        messagebox.showerror(
            "File In Use",
            f"Die Datei '{output_file}' ist derzeit in einem anderen Programm (z. B. Excel) geöffnet.\n"
            "Please close it and try again."
        )
    except Exception as e:
        messagebox.showerror("Fehler", f"Es ist ein unerwarteter Fehler aufgetreten:\n{e}")

                                                            # --- SELECT FOLDER FUNCTION --- #
def select_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        folder_var.set(folder_selected)
        # Check for combined_filtered.csv and enable/disable button accordingly
        filtered_csv = os.path.join(folder_selected, 'kombiniert_gefiltert.csv')
        if os.path.exists(filtered_csv):
            show_stats_btn.config(state="normal")
        else:
            show_stats_btn.config(state="disabled")

                                                            # --- COMBINE FILES INTO ONE CSV --- #
def run_combine():
    folder_path = folder_var.get()
    if not folder_path:
        messagebox.showwarning("Kein Ordner ausgewählt", "Bitte wählen Sie einen Ordner mit CSV-Dateien aus.")
        return
    combine_and_filter_csvs(folder_path)

                                                            # --- SHOW STATS NORMAL --- #
def show_stats_from_combined_filtered(folder_path):

    file_path = os.path.join(folder_path, 'kombiniert_gefiltert.csv')
    if not os.path.exists(file_path):
        messagebox.showerror("Fehler", "Die Datei kombiniert_gefiltert.csv existiert nicht. Bitte erstellen Sie sie zuerst.")
        return

    df = pd.read_csv(file_path, delimiter=';',low_memory=False)
    wert_cols = [col for col in df.columns if not (col.startswith("Datum") or col.startswith("Uhrzeit"))]
    rows = []

    # --- Collecting the period (earliest, latest datetime) ---
    date_times = []
    for wert_col in wert_cols:
        block_idx = df.columns.get_loc(wert_col) // 3
        col_date = df.columns[block_idx * 3]
        col_time = df.columns[block_idx * 3 + 1]
        dates = df[col_date].astype(str).fillna("")
        times = df[col_time].astype(str).fillna("")
        for d, t in zip(dates, times):
            dt_str = d.strip() + " " + t.strip()
            try:
                dt = datetime.strptime(dt_str, "%d.%m.%Y %H:%M:%S")
                date_times.append(dt)
            except:
                continue
    if date_times:
        earliest = min(date_times)
        latest = max(date_times)
        period_label = f"Zeitraum: {earliest.strftime('%d.%m.%Y %H:%M:%S')} bis {latest.strftime('%d.%m.%Y %H:%M:%S')}"
    else:
        period_label = "Zeitraum: -"
    # --------------------------------------------------------

    for wert_col in wert_cols:
        name = wert_col
        name = re.sub(r'B', r'_B', name, count=1)
        # Add mapped name if found in naming.csv mapping
        z_ba_pattern = re.search(r'Z\d_BA\d+', name) or re.search(r'Z\dBA\d+', name)
        if z_ba_pattern:
            z_ba_code = z_ba_pattern.group(0).replace('_', '')
            if z_ba_code in NAMING_DICT:
                name += NAMING_DICT[z_ba_code]

        wert_series = df[wert_col].astype(str).str.replace(",", ".")
        wert_series = pd.to_numeric(wert_series, errors='coerce').dropna()
        mean = round(wert_series.mean(), 4) if not wert_series.empty else ""
        median = round(wert_series.median(), 4) if not wert_series.empty else ""
        q1 = round(wert_series.quantile(0.25), 4) if not wert_series.empty else ""
        q3 = round(wert_series.quantile(0.75), 4) if not wert_series.empty else ""
        iqr = round(q3-q1, 4) if wert_series.size else ""
        rows.append([name, mean, median, q1, q3, iqr])

    try:
        rows.sort(key=lambda x: float(x[2]) if x[2] != "" else float('-inf'), reverse=True)
    except Exception:
        pass

    stat_win = Toplevel()
    def save_stats_pdf():
        from tkinter import filedialog
        pdf_path = filedialog.asksaveasfilename(defaultextension=".pdf", 
                                            filetypes=[("PDF files", "*.pdf")],
                                            title="PDF speichern")
        if pdf_path:
            # Use the current ML selection in the header
            current_ml = ml_var.get()  # <-- This gets the selected ML
            data = [columns] + rows
            export_pdf(data, pdf_path,
                   header=f"Taktzeit Auswertung {current_ml}",
                   subheader="Statistische Daten",
                   time_span=period_label)
        
    btn_pdf = tk.Button(stat_win, text="Als PDF speichern", command=save_stats_pdf, bg="#FFA500", fg="black")
    btn_pdf.pack(anchor="ne", padx=20, pady=(10, 2))
    stat_win.title("Kombinierte gefilterte CSV-Wertstatistiken")
    
    median_values = []
    for row in rows:
        try:
            median = float(row[2])
            if median <= 60:
                median_values.append(median)
        except:
            continue

    if median_values:
        max_median = max(median_values)
        soll_stueckzahl = round(((460*60)/max_median)*0.9, 2)
        info_text = f"Soll Stückzahl: {soll_stueckzahl}"
    else:
        info_text = "Soll Stückzahl: -"

    # Show period label above info_label/table
    period_label_widget = tk.Label(stat_win, text=period_label, font=("Arial", 11))
    period_label_widget.pack(pady=(10, 3))
    info_label = tk.Label(stat_win, text=info_text, font=("Arial", 12, "bold"))
    info_label.pack(pady=(10, 5))

    columns = ["Datensatz", "Mittelwert", "Median", "Q1", "Q3", "IQR"]
    frame = ttk.Frame(stat_win)
    frame.pack(expand=True, fill="both")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Orange.Treeview.Heading", background="#FFA500", foreground="black", font=("Aptos", 10, "bold"))
    style.configure("Orange.Treeview", font=("Arial", 10), rowheight=22)

    tree = ttk.Treeview(frame, columns=columns, show="headings", height=min(len(rows), 20), style="Orange.Treeview")
    sort_dirs = {col: False for col in columns}

    # Row coloring based on Median value
    tree.tag_configure("green", background="#9ae2b2")     # Light green #9ae2b2
    tree.tag_configure("red", background="#dba096")       # Light red #dba096

    for i, col in enumerate(columns):
        tree.heading(col, text=col, command=lambda _col=col: sortby(_col))
        if i == 0:
            tree.column(col, anchor='w', width=180)
        else:
            tree.column(col, anchor='center', width=100)

    def set_table_data(sorted_rows):
        tree.delete(*tree.get_children())
        # Check if user input is a valid 1-3 digit number
        soll_str = soll_taktzeit_var.get().strip()
        threshold = None
        if soll_str.isdigit() and 1 <= len(soll_str) <= 3:
            threshold = int(soll_str)
        for row in sorted_rows:
            tag = None
            try:
                median = float(row[2])
                if threshold is not None:
                    if median > threshold:
                        tag = "red"
                    else:
                        tag = "green"
            except:
                tag = None
            if tag:
                tree.insert("", "end", values=row, tags=(tag,))
            else:
                tree.insert("", "end", values=row)
    set_table_data(rows)

    def sortby(col_name):
        idx = columns.index(col_name)
        is_num_col = col_name != "Datensatz"
        reverse = sort_dirs[col_name]
        def try_float(val):
            try:
                return float(val)
            except:
                return float('-inf') if reverse else float('inf')
        if is_num_col:
            sorted_rows = sorted(rows, key=lambda x: try_float(x[idx]), reverse=not reverse)
        else:
            sorted_rows = sorted(rows, key=lambda x: x[idx], reverse=not reverse)
        sort_dirs[col_name] = not reverse
        set_table_data(sorted_rows)

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(side="left", expand=True, fill="both")

                                                            # --- CHECKBOX TICK AND SHOW SECOND FOLDER FIELD --- #
def toggle_vergleich():
    if vergleich_var.get():
        # Show second folder fields
        second_folder_label.grid(row=5, column=0, sticky="w")
        second_folder_entry.grid(row=6, column=0, padx=5, pady=2, sticky="w")
        second_folder_btn.grid(row=6, column=1, padx=1, pady=2, sticky="w")
        show_comparison_btn.config(state="normal")
    else:
        # Hide second folder fields
        second_folder_label.grid_remove()
        second_folder_entry.grid_remove()
        second_folder_btn.grid_remove()
        show_comparison_btn.config(state="disabled")
        second_folder_var.set("")

                                                            # --- SELECT SECOND FOLDER --- #       
def select_second_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        second_folder_var.set(folder_selected)
        
                                                            # --- COMPARE TWO STATS --- #
def show_stats_comparison(folder1, folder2):

    file1 = os.path.join(folder1, 'kombiniert_gefiltert.csv')
    file2 = os.path.join(folder2, 'kombiniert_gefiltert.csv')

    # Check if both files exist
    if not os.path.exists(file1):
        messagebox.showerror("Fehler", "Die Datei kombiniert_gefiltert.csv fehlt im ersten Ordner.\nBitte zuerst erzeugen oder Vergleich deaktivieren.")
        return
    if not os.path.exists(file2):
        messagebox.showerror("Fehler", "Die Datei kombiniert_gefiltert.csv fehlt im zweiten Ordner.\nBitte zuerst erzeugen oder Vergleich deaktivieren.")
        return

    df1 = pd.read_csv(file1, delimiter=';',low_memory=False)
    df2 = pd.read_csv(file2, delimiter=';',low_memory=False)
    
    cols1 = [col for col in df1.columns if not (col.startswith("Datum") or col.startswith("Uhrzeit"))]
    cols2 = [col for col in df2.columns if not (col.startswith("Datum") or col.startswith("Uhrzeit"))]

    stats1 = {}
    stats2 = {}

    median_vals1 = []
    median_vals2 = []

    def get_period_label(df):
        date_times = []
        columns = df.columns.tolist()
        # Step through every 3 columns (Datum, Uhrzeit, value)
        for block in range(0, len(columns), 3):
            if block+1 >= len(columns): continue
            col_date = columns[block]
            col_time = columns[block+1]
            dates = df[col_date].astype(str).fillna("")
            times = df[col_time].astype(str).fillna("")
            for d, t in zip(dates, times):
                dt_str = d.strip() + " " + t.strip()
                try:
                    dt = datetime.strptime(dt_str, "%d.%m.%Y %H:%M:%S")
                    date_times.append(dt)
                except:
                    continue
        if date_times:
            earliest = min(date_times)
            latest = max(date_times)
            return f"{earliest.strftime('%d.%m.%Y %H:%M:%S')} - {latest.strftime('%d.%m.%Y %H:%M:%S')}"
        else:
            return "-"
    
    # Collect stats for file 1
    for col in cols1:
        name = col
        name = re.sub(r'B', r'_B', name, count=1)
        
        # After you have 'name' in format Z7_BA02 (or Z7BA02 if _ is not present):
        z_ba_pattern = re.search(r'Z\d_BA\d+', name) or re.search(r'Z\dBA\d+', name)
        if z_ba_pattern:
            z_ba_code = z_ba_pattern.group(0).replace('_', '')  # Ensure no underscore in key as in CSV
            if z_ba_code in NAMING_DICT:
                name += NAMING_DICT[z_ba_code]
        
        series = df1[col].astype(str).str.replace(",", ".")
        series_num = pd.to_numeric(series, errors='coerce').dropna()
        mean = round(series_num.mean(), 4) if not series_num.empty else ""
        median = round(series_num.median(), 4) if not series_num.empty else ""
        stats1[name] = (mean, median)
        if median != "" and median <= 77:  # Only include medians <= 77, as in previous logic
            median_vals1.append(median)
    
    # Collect stats for file 2
    for col in cols2:
        name = col
        name = re.sub(r'B', r'_B', name, count=1)
        # After you have 'name' in format Z7_BA02 (or Z7BA02 if _ is not present):
        z_ba_pattern = re.search(r'Z\d_BA\d+', name) or re.search(r'Z\dBA\d+', name)
        if z_ba_pattern:
            z_ba_code = z_ba_pattern.group(0).replace('_', '')  # Ensure no underscore in key as in CSV
            if z_ba_code in NAMING_DICT:
                name += NAMING_DICT[z_ba_code]
        series = df2[col].astype(str).str.replace(",", ".")
        series_num = pd.to_numeric(series, errors='coerce').dropna()
        mean = round(series_num.mean(), 4) if not series_num.empty else ""
        median = round(series_num.median(), 4) if not series_num.empty else ""
        stats2[name] = (mean, median)
        if median != "" and median <= 77:
            median_vals2.append(median)

    # Stueckzahl calculation
    if median_vals1:
        max_median1 = max(median_vals1)
        stueckzahl1 = round(((460*60)/max_median1)*0.9, 2)
    else:
        stueckzahl1 = "-"

    if median_vals2:
        max_median2 = max(median_vals2)
        stueckzahl2 = round(((460*60)/max_median2)*0.9, 2)
    else:
        stueckzahl2 = "-"

    # Build comparison rows: only datasets present in BOTH files
    rows = []
    for name in sorted(stats1.keys()):
        if name in stats2:
            mean1, median1 = stats1[name]
            mean2, median2 = stats2[name]
            if median1 == "" or median2 == "":
                verbesserung = "-"
            else:
                try:
                    diff = median1 - median2
                    if median1 != 0:
                        percent_improvement = round(100 * diff / median1, 2)
                        verbesserung = f"{percent_improvement}%"
                    else:
                        verbesserung = "-"
                except Exception:
                    verbesserung = "-"
            rows.append([name, mean1, median1, mean2, median2, verbesserung])
    try:
        rows.sort(key=lambda x: float(x[4]) if x[4] != "" else float('-inf'), reverse=True)
    except Exception:
        pass

    # Show in new window
    stat_win = Toplevel()
    
    period_label1 = get_period_label(df1)
    period_label2 = get_period_label(df2)
    
    def save_comparison_pdf():
        from tkinter import filedialog
        pdf_path = filedialog.asksaveasfilename(defaultextension=".pdf", 
                                            filetypes=[("PDF files", "*.pdf")],
                                            title="PDF speichern")
        if pdf_path:
            current_ml = ml_var.get()
            # Compose period string as required:
            zeitraume_text = f"{period_label1} und {period_label2}"
            data = [columns] + rows
            export_pdf(data, pdf_path,
                   header=f"Taktzeit Auswertung {current_ml}",
                   subheader="Vergleich der Zeiträume",
                   time_span=zeitraume_text)

    btn_pdf = tk.Button(stat_win, text="Als PDF speichern", command=save_comparison_pdf, bg="#FFA500", fg="black")
    btn_pdf.pack(anchor="ne", padx=20, pady=(10, 2))
    stat_win.title("Vergleich von CSV-Statistiken")

    # Show Stueckzahl labels above the table
    info_label1 = tk.Label(stat_win, text=f"Stueckzahl 1: {stueckzahl1}", font=("Arial", 12, "bold"))
    info_label1.pack(pady=(10, 3))
    info_label2 = tk.Label(stat_win, text=f"Stueckzahl 2: {stueckzahl2}", font=("Arial", 12, "bold"))
    info_label2.pack(pady=(0, 8))

    columns = ["Datensatz", "Mittelwert 1", "Median 1", "Mittelwert 2", "Median 2", "Verbesserung"]
    frame = ttk.Frame(stat_win)
    frame.pack(expand=True, fill="both")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Blue.Treeview.Heading", background="#A3CEF1", foreground="black", font=("Aptos", 10, "bold"))
    style.configure("Blue.Treeview", font=("Arial", 10), rowheight=22)

    tree = ttk.Treeview(frame, columns=columns, show="headings", height=min(len(rows), 20), style="Blue.Treeview")

 # Tag styles for row coloring based on 'Verbesserung'
    tree.tag_configure("improved", background="#9ae2b2")    # Light green
    tree.tag_configure("worse", background="#dba096")       # Light red

    sort_dirs = {col: False for col in columns}

    def set_table_data(sorted_rows):
        tree.delete(*tree.get_children())
        for row in sorted_rows:
            verbesserung = row[-1]
            tag = None
            try:
                perc = float(str(verbesserung).replace("%", "").replace(",", "."))
                if perc > 0:
                    tag = "improved"
                elif perc < 0:
                    tag = "worse"
            except:
                tag = None
            if tag:
                tree.insert("", "end", values=row, tags=(tag,))
            else:
                tree.insert("", "end", values=row)
    set_table_data(rows)

    def sortby(col_name):
        idx = columns.index(col_name)
        # For numeric columns except Datensatz and Verbesserung
        is_num_col = col_name not in ["Datensatz", "Verbesserung"]
        reverse = sort_dirs[col_name]
        def try_float(val):
            # For 'Verbesserung', extract percent if present
            if col_name == "Verbesserung":
                try:
                    return float(str(val).replace("%", ""))
                except:
                    return float('-inf') if reverse else float('inf')
            try:
                return float(val)
            except:
                return float('-inf') if reverse else float('inf')
        if is_num_col or col_name == "Verbesserung":
            sorted_rows = sorted(rows, key=lambda x: try_float(x[idx]), reverse=not reverse)
        else:
            sorted_rows = sorted(rows, key=lambda x: x[idx], reverse=not reverse)
        sort_dirs[col_name] = not reverse
        set_table_data(sorted_rows)

    for i, col in enumerate(columns):
        tree.heading(col, text=col, command=lambda _col=col: sortby(_col))
        if i == 0:
            tree.column(col, anchor='w', width=180)
        else:
            tree.column(col, anchor='center', width=110)

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(side="left", expand=True, fill="both")

                                                            # --- GUI CREATION --- #
root = tk.Tk()
root.title("CSV Combiner")


default_font = tkfont.nametofont("TkDefaultFont")
default_font.config(family="BMWGroupTN Condensed", size=11)
# (Optional for ttk)
root.option_add("*Font", default_font)
root.option_add("*TButton*Font", default_font)
root.option_add("*TLabel*Font", default_font)
root.option_add("*TEntry*Font", default_font)
folder_var = tk.StringVar()

# Load the image
try:
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    logo_img = Image.open(logo_path)
    scale = 0.15
    w = int(logo_img.size[0] * scale)
    h = int(logo_img.size[1] * scale)
    logo_img = logo_img.resize((w, h), Image.LANCZOS)
    logo_photo = ImageTk.PhotoImage(logo_img)
    logo_label = tk.Label(root, image=logo_photo, bg=None)  # root instead of frm!
    logo_label.image = logo_photo
    logo_label.pack(side="top", anchor="nw", padx=20, pady=15)
except Exception as e:
    print(f"Logo konnte nicht geladen werden: {e}")
    
frm = tk.Frame(root, padx=20, pady=20)

frm.pack()

# Path selection row
tk.Label(frm, text="Ordner mit CSV-Dateien auswählen:").grid(row=0, column=0, sticky="w", pady=(0, 2))
tk.Entry(frm, textvariable=folder_var, width=50).grid(row=1, column=0, padx=5, pady=2)
tk.Button(frm, text="Durchsuchen...", command=select_folder).grid(row=1, column=1, padx=1, pady=2, sticky="w")

# Soll-Taktzeit field under Path field
soll_taktzeit_var = tk.StringVar()
# Soll-Taktzeit field directly under Path
soll_taktzeit_var = tk.StringVar()
soll_frame = tk.Frame(frm)
soll_frame.grid(row=2, column=0, sticky="w", pady=(8, 2), columnspan=2)  # Span 2 columns for alignment

tk.Label(soll_frame, text="Soll-Taktzeit (s):").pack(side="left")
tk.Entry(soll_frame, textvariable=soll_taktzeit_var, width=5).pack(side="left", padx=(5, 0))

# ML Selector
ml_var = tk.StringVar(value="ML8")  # default selection

def update_soll_from_ml(*args):
    if ml_var.get() == "ML8":
        soll_taktzeit_var.set("72")
    elif ml_var.get() == "ML12":
        soll_taktzeit_var.set("30")

ml_var.trace_add("write", update_soll_from_ml)

tk.Label(soll_frame, text="ML wählen:").pack(side="left", padx=(10,0))
ml_selector = tk.OptionMenu(soll_frame, ml_var, "ML8", "ML12")
ml_selector.pack(side="left", padx=(5, 0))

# Combine and Stats buttons on the same line
combine_btn = tk.Button(frm, text="CSV-Dateien kombinieren und filtern", command=run_combine, bg="#2196F3", fg='white')
combine_btn.grid(row=3, column=0, pady=(12, 10), padx=0, sticky="ew")

show_stats_btn = tk.Button(frm, text="Statistische Daten anzeigen", state="disabled",
    command=lambda: show_stats_from_combined_filtered(folder_var.get()), bg='#FFC107')
show_stats_btn.grid(row=3, column=1, pady=(12, 10), padx=5, sticky="ew")

# "Vergleichen" checkbox and second folder field, hidden by default
vergleich_var = tk.BooleanVar()
tk.Checkbutton(frm, text="Vergleichen", variable=vergleich_var, command=lambda: toggle_vergleich()).grid(row=4, column=0, sticky="w", pady=2)

second_folder_var = tk.StringVar()
second_folder_label = tk.Label(frm, text="Zweiter Ordner mit CSV-Dateien:")
second_folder_entry = tk.Entry(frm, textvariable=second_folder_var, width=50)
second_folder_btn = tk.Button(frm, text="Durchsuchen...", command=lambda: select_second_folder())

# Show comparison button (initially disabled)
show_comparison_btn = tk.Button(frm, text="Statistiken Vergleich anzeigen", state="disabled",
    command=lambda: show_stats_comparison(folder_var.get(), second_folder_var.get()), bg="#A3CEF1")
show_comparison_btn.grid(row=7, column=0, columnspan=2, pady=(12,0), sticky="ew")


root.mainloop()