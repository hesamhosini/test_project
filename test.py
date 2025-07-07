import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json, csv, configparser, yaml, toml, os
import xml.etree.ElementTree as ET
import pandas as pd

# ---------- ابزارهای کمکی ----------
def detect_format(filename):
    return os.path.splitext(filename)[1].lower()

def xml_to_dict(elem):
    d = {}
    for child in elem:
        if len(child):
            d[child.tag] = xml_to_dict(child)
        else:
            d[child.tag] = child.text
    return d

def dict_to_xml(data, root_tag="root"):
    root = ET.Element(root_tag)

    def build_elem(parent, val):
        if isinstance(val, dict):
            for k, v in val.items():
                child = ET.SubElement(parent, k)
                build_elem(child, v)
        elif isinstance(val, list):
            for item in val:
                item_elem = ET.SubElement(parent, "item")
                build_elem(item_elem, item)
        else:
            parent.text = str(val)

    build_elem(root, data)
    return root

# ---------- خواندن ----------
def read_file(path):
    ext = detect_format(path)
    with open(path, 'r', encoding='utf-8') as f:
        if ext in ['.json', '.jsonld', '.json-ld']:
            return json.load(f)
        elif ext == '.ndjson':
            data = []
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))
            return data
        elif ext == '.csv':
            reader = csv.DictReader(f)
            return list(reader)
        elif ext == '.ini':
            config = configparser.ConfigParser()
            config.read_file(f)
            return {s: dict(config[s]) for s in config.sections()}
        elif ext in ['.yaml', '.yml']:
            return yaml.safe_load(f)
        elif ext == '.toml':
            return toml.load(f)
        elif ext == '.xml':
            tree = ET.parse(f)
            root = tree.getroot()
            return {root.tag: xml_to_dict(root)}
        elif ext == '.parquet':
            df = pd.read_parquet(path)
            return df.to_dict(orient='records')
        else:
            raise ValueError("فرمت پشتیبانی نمی‌شود")

# ---------- نوشتن ----------
def write_file(data, path, format_):
    if format_ == 'parquet':
        if isinstance(data, dict):
            data = [data]
        df = pd.DataFrame(data)
        df.to_parquet(path, index=False)
        return

    with open(path, 'w', encoding='utf-8', newline='') as f:
        if format_ in ['json', 'jsonld', 'json-ld']:
            json.dump(data, f, indent=4, ensure_ascii=False)
        elif format_ == 'ndjson':
            if isinstance(data, dict):
                data = [data]
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        elif format_ == 'csv':
            if isinstance(data, dict):
                data = [data]
            if isinstance(data, list) and isinstance(data[0], dict):
                keys = set()
                for row in data:
                    keys.update(row.keys())
                keys = list(keys)
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for row in data:
                    writer.writerow({k: str(row.get(k, "")) for k in keys})
            else:
                raise ValueError("CSV نیاز به لیستی از دیکشنری‌ها دارد.")
        elif format_ == 'ini':
            config = configparser.ConfigParser()
            for section, values in data.items():
                if isinstance(values, dict):
                    config[section] = {str(k): str(v) for k, v in values.items()}
                else:
                    config[section] = {'value': str(values)}
            config.write(f)
        elif format_ == 'yaml':
            yaml.dump(data, f, allow_unicode=True)
        elif format_ == 'toml':
            toml.dump(data, f)
        elif format_ == 'xml':
            root_tag = list(data.keys())[0] if isinstance(data, dict) and len(data) == 1 else "root"
            root = dict_to_xml(data[root_tag] if root_tag != "root" else data, root_tag)
            tree = ET.ElementTree(root)
            tree.write(f, encoding='unicode', xml_declaration=True)
        else:
            raise ValueError("فرمت خروجی پشتیبانی نمی‌شود")

# ---------- رابط گرافیکی ----------
class FileConverterApp:
    def __init__(self, master):
        self.master = master
        self.master.title("🧰 مبدل فرمت فایل‌ها")
        self.master.geometry("600x500")
        self.data = None

        self.setup_ui()

    def setup_ui(self):
        frm = ttk.Frame(self.master, padding=10)
        frm.pack(fill='both', expand=True)

        ttk.Label(frm, text="فرمت خروجی را انتخاب کنید:", font=('Segoe UI', 11)).pack(pady=10)

        self.output_var = tk.StringVar()
        formats = ['json', 'jsonld', 'json-ld', 'ndjson', 'csv', 'xml', 'ini', 'yaml', 'toml', 'parquet']
        ttk.Combobox(frm, textvariable=self.output_var, values=formats, state="readonly").pack()

        ttk.Button(frm, text="📂 انتخاب فایل و تبدیل", command=self.convert).pack(pady=15)

        ttk.Label(frm, text="پیش‌نمایش داده:", font=('Segoe UI', 11, 'bold')).pack(pady=(20, 5))
        self.preview = tk.Text(frm, height=15, wrap='word', font=('Consolas', 10))
        self.preview.pack(fill='both', expand=True, padx=10)

    def convert(self):
        input_file = filedialog.askopenfilename(title="انتخاب فایل ورودی")
        if not input_file:
            return
        try:
            self.data = read_file(input_file)
            preview_text = json.dumps(self.data, indent=2, ensure_ascii=False)
            self.preview.delete("1.0", tk.END)
            self.preview.insert(tk.END, preview_text[:3000])  # نمایش محدود شده
        except Exception as e:
            messagebox.showerror("❌ خطا در خواندن", str(e))
            return

        output_format = self.output_var.get()
        if not output_format:
            messagebox.showwarning("⚠️ هشدار", "لطفاً فرمت خروجی را انتخاب کنید")
            return

        output_file = filedialog.asksaveasfilename(defaultextension=f".{output_format}",
                                                   filetypes=[(f"{output_format.upper()} files", f"*.{output_format}")])
        if not output_file:
            return

        try:
            write_file(self.data, output_file, output_format)
            messagebox.showinfo("✅ موفقیت", f"فایل با موفقیت به {output_format.upper()} تبدیل شد!")
        except Exception as e:
            messagebox.showerror("❌ خطا در نوشتن", str(e))

# ---------- اجرا ----------
if __name__ == '__main__':
    root = tk.Tk()
    style = ttk.Style(root)
    style.theme_use('clam')
    app = FileConverterApp(root)
    root.mainloop()
