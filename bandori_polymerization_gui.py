import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


FILE_PATH = os.path.join(os.path.dirname(__file__), "bandori_polymerization.json")
FIELDS = [
    ("id", "ID"),
    ("province", "省份"),
    ("name", "名称"),
    ("info", "信息"),
    ("type", "类型"),
    ("verified", "已验证"),
    ("raw_text", "原始文本"),
    ("created_at", "创建日期"),
    ("project", "项目"),
]

PROVINCES = [
    "北京", "天津", "上海", "重庆",
    "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "海南",
    "四川", "贵州", "云南", "陕西", "甘肃", "青海",
    "台湾",
    "内蒙古", "广西", "西藏", "宁夏", "新疆",
    "香港", "澳门",
    "海外",
]

TYPE_OPTIONS = ["non-regional", "school", "region"]


class BandoriPolymerizationApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Bandori Polymerization JSON 管理器")
        self.root.geometry("1500x820")
        self.root.minsize(1280, 760)

        self.entries = {}
        self.variables = {}
        self.records = []
        self.selected_tree_item = None

        self._build_ui()
        self.load_data()

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = ttk.LabelFrame(main_frame, text="数据列表", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_frame = ttk.LabelFrame(main_frame, text="记录编辑", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))
        right_frame.configure(width=320)
        right_frame.pack_propagate(False)

        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(search_frame, text="搜索：").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))
        search_entry.bind("<KeyRelease>", lambda event: self.refresh_tree())

        ttk.Button(search_frame, text="刷新", command=self.load_data).pack(side=tk.LEFT)

        columns = [field for field, _ in FIELDS]
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=22)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        for field, label in FIELDS:
            self.tree.heading(field, text=label)
            width = 110
            if field in {"name", "raw_text", "info"}:
                width = 180
            self.tree.column(field, width=width, anchor=tk.W)

        form_frame = ttk.Frame(right_frame)
        form_frame.pack(fill=tk.BOTH, expand=True)

        for row_index, (field, label) in enumerate(FIELDS):
            ttk.Label(form_frame, text=f"{label}：").grid(row=row_index, column=0, sticky=tk.W, pady=4)

            if field == "id":
                entry = ttk.Entry(form_frame, width=36, state="readonly")
            elif field == "province":
                variable = tk.StringVar()
                entry = ttk.Combobox(form_frame, textvariable=variable, values=PROVINCES, width=33)
                entry.bind("<KeyRelease>", self.on_province_keyrelease)
                entry.bind("<Button-1>", lambda event: self.filter_province_options())
                self.variables[field] = variable
            elif field == "type":
                variable = tk.StringVar()
                entry = ttk.Combobox(form_frame, textvariable=variable, values=TYPE_OPTIONS, state="readonly", width=33)
                self.variables[field] = variable
            elif field == "verified":
                variable = tk.BooleanVar(value=False)
                entry = ttk.Checkbutton(form_frame, variable=variable, text="已验证")
                self.variables[field] = variable
            elif field == "created_at":
                entry = ttk.Entry(form_frame, width=36, state="readonly")
            elif field == "project":
                entry = ttk.Entry(form_frame, width=36)
            else:
                entry = ttk.Entry(form_frame, width=36)

            entry.grid(row=row_index, column=1, sticky=tk.EW, pady=4)
            self.entries[field] = entry

        form_frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X, pady=(12, 0))

        ttk.Button(button_frame, text="新增", command=self.add_record).pack(fill=tk.X, pady=3)
        ttk.Button(button_frame, text="修改", command=self.update_record).pack(fill=tk.X, pady=3)
        ttk.Button(button_frame, text="删除", command=self.delete_record).pack(fill=tk.X, pady=3)
        ttk.Button(button_frame, text="清空表单", command=self.clear_form).pack(fill=tk.X, pady=3)

        tip_text = (
            "说明：\n"
            "1. 左侧显示 JSON 中 data 列表。\n"
            "2. 选中一条记录后可在右侧修改。\n"
            "3. 新增时会自动分配 ID 和创建日期。\n"
            "4. type 使用固定选项，province 支持输入模糊筛选。\n"
            "5. verified 保存为 1 或 0，raw_text 自动拼接。\n"
            "6. project 默认填充为 bandori。\n"
            "7. 保存后会自动更新 success 与 total 字段。"
        )
        ttk.Label(right_frame, text=tip_text, justify=tk.LEFT).pack(anchor=tk.W, pady=(12, 0))

    def load_data(self):
        data = self.read_json()
        self.records = data.get("data", [])
        self.normalize_record_ids()
        self.write_json()
        self.refresh_tree()
        self.clear_form()

    def read_json(self):
        if not os.path.exists(FILE_PATH):
            return {"success": True, "total": 0, "data": []}

        with open(FILE_PATH, "r", encoding="utf-8") as file:
            return json.load(file)

    def write_json(self):
        payload = {
            "success": True,
            "total": len(self.records),
            "data": self.records,
        }
        with open(FILE_PATH, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=4)

    def refresh_tree(self):
        keyword = self.search_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())

        for record in self.records:
            searchable_text = json.dumps(record, ensure_ascii=False).lower()
            if keyword and keyword not in searchable_text:
                continue

            values = [record.get(field, "") for field, _ in FIELDS]
            self.tree.insert("", tk.END, values=values)

    def on_tree_select(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        selected_item = selected_items[0]
        values = self.tree.item(selected_item, "values")

        self.clear_form(reset_selection=False)
        self.selected_tree_item = selected_item
        for index, (field, _) in enumerate(FIELDS):
            self.set_field_value(field, values[index])

    def clear_form(self, reset_selection=True):
        if reset_selection:
            self.selected_tree_item = None
            self.tree.selection_remove(self.tree.selection())

        for field, entry in self.entries.items():
            if field == "verified":
                self.variables[field].set(False)
                continue
            if field in {"province", "type"}:
                self.variables[field].set("")
                continue
            self.set_entry_text(entry, "")

        self.set_entry_text(self.entries["id"], str(self.get_next_id()))
        self.set_entry_text(self.entries["created_at"], self.get_today())
        self.set_entry_text(self.entries["project"], "bandori")
        self.set_entry_text(self.entries["raw_text"], "")
        self.variables["type"].set("non-regional")

    def set_entry_text(self, entry, value):
        state = str(entry.cget("state"))
        if state == "readonly":
            entry.config(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, value)
            entry.config(state="readonly")
            return

        entry.delete(0, tk.END)
        entry.insert(0, value)

    def set_field_value(self, field, value):
        if field == "verified":
            if isinstance(value, str):
                normalized = value.strip().lower()
                self.variables[field].set(normalized in {"1", "true", "yes"})
            else:
                self.variables[field].set(bool(value))
            return

        if field in {"province", "type"}:
            self.variables[field].set(str(value))
            if field == "province":
                self.entries[field]["values"] = PROVINCES
            return

        self.set_entry_text(self.entries[field], str(value))

    def on_province_keyrelease(self, event=None):
        self.filter_province_options()

    def filter_province_options(self):
        keyword = self.variables["province"].get().strip()
        if not keyword:
            matched = PROVINCES
        else:
            matched = [province for province in PROVINCES if keyword in province]

        self.entries["province"]["values"] = matched
        if matched:
            self.entries["province"].event_generate("<Down>")

    def get_form_data(self):
        record = {}
        for field, _ in FIELDS:
            if field == "verified":
                record[field] = 1 if self.variables[field].get() else 0
            elif field in {"province", "type"}:
                record[field] = self.variables[field].get().strip()
            else:
                record[field] = self.entries[field].get().strip()

        if not record["name"]:
            raise ValueError("名称不能为空")

        if record["type"] not in TYPE_OPTIONS:
            raise ValueError("类型只能是 non-regional、school 或 region")

        if record["id"]:
            try:
                record["id"] = int(record["id"])
            except ValueError as exc:
                raise ValueError("ID 必须是整数") from exc
        else:
            record["id"] = self.get_next_id()

        record["created_at"] = record["created_at"] or self.get_today()
        record["project"] = record["project"] or "bandori"
        if not record["raw_text"]:
            record["raw_text"] = self.build_raw_text(record["name"], record["info"])

        return record

    def get_next_id(self):
        existing_ids = [int(item.get("id", 0)) for item in self.records if str(item.get("id", "")).isdigit()]
        return max(existing_ids, default=0) + 1

    def get_today(self):
        return datetime.now().strftime("%Y-%m-%d")

    def build_raw_text(self, name, info):
        name = name.strip()
        info = info.strip()
        return f"{name} {info}".strip()

    def normalize_record_ids(self):
        self.records.sort(key=lambda item: int(item.get("id", 0)) if str(item.get("id", "")).isdigit() else 0)
        for index, record in enumerate(self.records, start=1):
            record["id"] = index

    def add_record(self):
        try:
            record = self.get_form_data()
        except ValueError as error:
            messagebox.showerror("新增失败", str(error))
            return

        if any(int(item.get("id", 0)) == record["id"] for item in self.records):
            messagebox.showerror("新增失败", f"ID {record['id']} 已存在")
            return

        self.records.append(record)
        self.write_json()
        self.refresh_tree()
        self.clear_form()
        messagebox.showinfo("新增成功", "记录已新增并保存到 JSON 文件")

    def update_record(self):
        try:
            record = self.get_form_data()
        except ValueError as error:
            messagebox.showerror("修改失败", str(error))
            return

        if self.selected_tree_item is None:
            messagebox.showwarning("修改失败", "请先在左侧选择一条记录")
            return

        selected_values = self.tree.item(self.selected_tree_item, "values")
        original_id = int(selected_values[0])

        for index, item in enumerate(self.records):
            item_id = int(item.get("id", 0))
            if item_id == record["id"] and item_id != original_id:
                messagebox.showerror("修改失败", f"ID {record['id']} 已被其他记录占用")
                return
            if item_id == original_id:
                self.records[index] = record
                self.write_json()
                self.refresh_tree()
                self.clear_form()
                messagebox.showinfo("修改成功", "记录已更新并保存到 JSON 文件")
                return

        messagebox.showerror("修改失败", "未找到对应记录，可能数据已变化，请刷新后重试")

    def delete_record(self):
        if self.selected_tree_item is None:
            messagebox.showwarning("删除失败", "请先在左侧选择一条记录")
            return

        selected_values = self.tree.item(self.selected_tree_item, "values")
        target_id = int(selected_values[0])

        if not messagebox.askyesno("确认删除", f"确定删除 ID 为 {target_id} 的记录吗？"):
            return

        self.records = [item for item in self.records if int(item.get("id", 0)) != target_id]
        self.write_json()
        self.refresh_tree()
        self.clear_form()
        messagebox.showinfo("删除成功", "记录已删除并保存到 JSON 文件")


def main():
    root = tk.Tk()
    app = BandoriPolymerizationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
