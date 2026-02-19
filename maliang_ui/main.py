import os
import threading
from tkinter import filedialog, messagebox

import maliang
from PIL import Image, ImageTk
from rembg import new_session, remove


class RembgApp:
    def __init__(self):
        self.root = maliang.Tk(size=(1000, 700), title="Rembg 背景去除工具")
        self.root.center()

        # 状态变量
        self.input_path = None
        self.output_image = None
        self.models = [
            "u2net",
            "u2netp",
            "u2net_human_seg",
            "u2net_cloth_seg",
            "silueta",
            "isnet-general-use",
            "isnet-anime",
            "birefnet-general",
            "birefnet-general-lite",
            "birefnet-portrait",
            "birefnet-dis",
            "birefnet-HRSOD",
            "birefnet-cod",
            "birefnet-massive",
            "bria-rmbg",
        ]
        self.current_model = self.models[0]
        self.session = new_session(self.current_model)
        self.alpha_var = False
        self.is_processing = False  # 防止重复处理

        # 主画布
        self.cv = maliang.Canvas(auto_zoom=True, keep_ratio="min", free_anchor=True)
        self.cv.place(width=1280, height=720, x=640, y=360, anchor="center")

        self.create_widgets()
        self.root.mainloop()

    def on_model_selected_combo(self, index):
        """当用户在 ComboBox 中选择新模型时调用，index 为选项索引（从0开始）"""
        self.current_model = self.models[int(index)]
        self.session = new_session(self.current_model)
        messagebox.showinfo("模型切换", f"已切换到模型: {self.current_model}")

    def create_widgets(self):
        # 标题
        maliang.Text(
            self.cv, (640, 50), text="背景去除工具", fontsize=48, anchor="center"
        )

        # 文件选择
        maliang.Text(self.cv, (200, 150), text="选择图片:", anchor="nw")
        self.btn_select = maliang.Button(
            self.cv, (300, 140), (100, 30), text="浏览", command=self.select_file
        )
        # 文件标签（不再动态更新）
        self.file_label = maliang.Text(
            self.cv, (420, 150), text="未选择文件", anchor="nw", fontsize=12
        )

        # 模型选择（ComboBox）
        maliang.Text(self.cv, (200, 200), text="选择模型:", anchor="nw")
        self.model_combo = maliang.ComboBox(
            self.cv,
            (300, 190),  # 位置 (x, y)
            text=self.models,  # 传入模型名称列表
            command=self.on_model_selected_combo,  # 选中后执行的回调
        )

        maliang.Text(self.cv, (200, 250), text="Alpha matting:", anchor="nw")
        self.alpha_switch = maliang.Switch(
            self.cv, (350, 250), command=self.on_alpha_toggle, default=False
        )

        # 处理按钮（始终可用，但通过 is_processing 控制）
        self.btn_process = maliang.Button(
            self.cv, (200, 300), (150, 40), text="去除背景", command=self.start_remove
        )

        # 保存按钮（始终可用）
        self.btn_save = maliang.Button(
            self.cv, (400, 300), (150, 40), text="保存结果", command=self.save_result
        )

        # 进度提示（不再动态更新）
        self.progress_text = maliang.Text(
            self.cv, (600, 310), text="", anchor="nw", fontsize=12
        )

        # 原图预览画布
        maliang.Text(self.cv, (550, 100), text="原图预览", anchor="nw")
        self.orig_canvas = maliang.Canvas(
            self.cv, width=200, height=200, bg="gray", highlightthickness=0
        )
        self.orig_canvas.place(x=550, y=130, anchor="nw")

        # 结果预览画布
        maliang.Text(self.cv, (550, 350), text="结果预览", anchor="nw")
        self.result_canvas = maliang.Canvas(
            self.cv, width=200, height=200, bg="gray", highlightthickness=0
        )
        self.result_canvas.place(x=550, y=380, anchor="nw")

    def on_alpha_toggle(self, state):
        self.alpha_var = state

    def on_model_selected(self, index):
        """当用户在 OptionButton 中选择新模型时调用，index 为选项索引（从0开始）"""
        self.current_model = self.models[int(index)]  # 将索引转为整数，获取模型名
        self.session = new_session(self.current_model)
        messagebox.showinfo("模型切换", f"已切换到模型: {self.current_model}")

    def select_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        if path:
            self.input_path = path
            # 不更新标签文本，仅预览图片
            self.show_image_on_canvas(path, self.orig_canvas)

    def show_image_on_canvas(self, path, canvas):
        img = Image.open(path)
        # 获取画布实际尺寸
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        # 缩放到画布内（保持比例）
        img.thumbnail((canvas_width, canvas_height))
        self.tk_img = ImageTk.PhotoImage(img)
        canvas.delete("all")
        # 计算居中位置
        x = (canvas_width - img.width) // 2
        y = (canvas_height - img.height) // 2
        canvas.create_image(x, y, image=self.tk_img, anchor="nw")
        canvas.image = self.tk_img

    def switch_model(self):
        idx = self.models.index(self.current_model)
        self.current_model = self.models[(idx + 1) % len(self.models)]
        # 不更新标签文本，仅用消息框提示
        self.session = new_session(self.current_model)
        messagebox.showinfo("模型切换", f"已切换到模型: {self.current_model}")

    def toggle_alpha(self):
        self.alpha_var = not self.alpha_var
        state = "开" if self.alpha_var else "关"
        # 不更新按钮文本，仅内部记录
        # 可考虑用 messagebox 提示，但太频繁，暂时不处理

    def start_remove(self):
        if self.is_processing:
            messagebox.showwarning("提示", "正在处理中，请稍后")
            return
        if not self.input_path:
            messagebox.showwarning("提示", "请先选择图片")
            return

        self.is_processing = True
        # 不更新界面，直接启动线程
        threading.Thread(target=self.remove_background, daemon=True).start()

    def remove_background(self):
        try:
            with open(self.input_path, "rb") as f:
                input_data = f.read()
            output_data = remove(
                input_data, session=self.session, alpha_matting=self.alpha_var
            )
            from io import BytesIO

            self.output_image = Image.open(BytesIO(output_data))

            self.root.after(0, self.display_result)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
        finally:
            self.root.after(0, self.finish_processing)

    def display_result(self):
        thumb = self.output_image.copy()
        thumb.thumbnail((300, 300))
        self.result_tk = ImageTk.PhotoImage(thumb)
        self.result_canvas.delete("all")
        self.result_canvas.create_image(150, 150, image=self.result_tk)
        self.result_canvas.image = self.result_tk
        # 不更新进度文本，但可以弹出提示
        messagebox.showinfo("完成", "背景去除完成！")

    def finish_processing(self):
        self.is_processing = False

    def save_result(self):
        if self.output_image is None:
            messagebox.showwarning("提示", "没有可保存的结果")
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG files", "*.png")]
        )
        if save_path:
            self.output_image.save(save_path)
            messagebox.showinfo("保存成功", f"图片已保存至 {save_path}")


if __name__ == "__main__":
    RembgApp()
