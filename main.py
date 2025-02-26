import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import random
import time

class MemoryBlock:
    """内存块类，用于动态分区管理"""
    def __init__(self, start_addr, size, allocated=False, process_id=None):
        self.start_addr = start_addr  # 起始地址
        self.size = size              # 大小
        self.allocated = allocated    # 是否已分配
        self.process_id = process_id  # 分配给的进程ID

    def __str__(self):
        status = "已分配给进程" + str(self.process_id) if self.allocated else "空闲"
        return f"[{self.start_addr}-{self.start_addr+self.size-1}, 大小: {self.size}, {status}]"

class Process:
    """进程类"""
    def __init__(self, pid, memory_size):
        self.pid = pid
        self.memory_size = memory_size
        self.allocated_block = None  # 分配的内存块

class DynamicPartition:
    """动态分区管理类"""
    def __init__(self, memory_size=1024):
        self.memory_size = memory_size
        self.memory_blocks = [MemoryBlock(0, memory_size)]  # 初始时只有一个大的空闲块
        self.processes = {}  # 存储所有进程
        
    def allocate(self, process, algorithm="first_fit"):
        """分配内存给进程"""
        if process.pid in self.processes:
            return False, f"进程 {process.pid} 已存在"
        
        # 根据不同算法选择合适的空闲块
        free_blocks = [block for block in self.memory_blocks if not block.allocated]
        suitable_block = None
        suitable_index = -1
        
        if algorithm == "first_fit":
            # 最先适应算法
            for i, block in enumerate(free_blocks):
                if block.size >= process.memory_size:
                    suitable_block = block
                    suitable_index = self.memory_blocks.index(block)
                    break
                    
        elif algorithm == "best_fit":
            # 最佳适应算法
            min_size_diff = float('inf')
            for i, block in enumerate(free_blocks):
                if block.size >= process.memory_size and block.size - process.memory_size < min_size_diff:
                    min_size_diff = block.size - process.memory_size
                    suitable_block = block
                    suitable_index = self.memory_blocks.index(block)
                    
        elif algorithm == "worst_fit":
            # 最坏适应算法
            max_size_diff = -1
            for i, block in enumerate(free_blocks):
                if block.size >= process.memory_size and block.size - process.memory_size > max_size_diff:
                    max_size_diff = block.size - process.memory_size
                    suitable_block = block
                    suitable_index = self.memory_blocks.index(block)
        
        # 如果找到合适的块，进行分配
        if suitable_block:
            start_addr = suitable_block.start_addr
            original_size = suitable_block.size
            
            # 分配内存给进程
            allocated_block = MemoryBlock(start_addr, process.memory_size, True, process.pid)
            process.allocated_block = allocated_block
            
            # 更新内存块列表
            self.memory_blocks.pop(suitable_index)
            
            # 如果分配后还有剩余空间，创建新的空闲块
            if original_size > process.memory_size:
                remaining_block = MemoryBlock(
                    start_addr + process.memory_size,
                    original_size - process.memory_size
                )
                self.memory_blocks.insert(suitable_index, remaining_block)
                
            self.memory_blocks.insert(suitable_index, allocated_block)
            self.processes[process.pid] = process
            
            return True, f"成功为进程 {process.pid} 分配内存"
        else:
            return False, f"无法为进程 {process.pid} 分配 {process.memory_size} 单位内存"
    
    def deallocate(self, pid):
        """释放进程占用的内存"""
        if pid not in self.processes:
            return False, f"进程 {pid} 不存在"
            
        process = self.processes[pid]
        allocated_block = None
        
        # 找到该进程分配的内存块
        for i, block in enumerate(self.memory_blocks):
            if block.allocated and block.process_id == pid:
                allocated_block = block
                block_index = i
                break
                
        if not allocated_block:
            return False, f"进程 {pid} 没有分配内存块"
            
        # 释放内存块
        free_block = MemoryBlock(allocated_block.start_addr, allocated_block.size)
        self.memory_blocks[block_index] = free_block
        
        # 合并相邻的空闲块
        self._merge_adjacent_blocks()
        
        # 删除进程
        del self.processes[pid]
        
        return True, f"成功释放进程 {pid} 的内存"
    
    def _merge_adjacent_blocks(self):
        """合并相邻的空闲块"""
        i = 0
        while i < len(self.memory_blocks) - 1:
            current_block = self.memory_blocks[i]
            next_block = self.memory_blocks[i + 1]
            
            # 如果当前块和下一个块都是空闲的，合并它们
            if not current_block.allocated and not next_block.allocated:
                current_block.size += next_block.size
                self.memory_blocks.pop(i + 1)
            else:
                i += 1
    
    def get_memory_status(self):
        """获取内存状态"""
        return [str(block) for block in self.memory_blocks]

class Page:
    """页面类"""
    def __init__(self, page_no, exists=False, frame_no=None, modified=False, disk_pos=None):
        self.page_no = page_no      # 页号
        self.exists = exists        # 是否在内存中
        self.frame_no = frame_no    # 内存块号
        self.modified = modified    # 修改标志
        self.disk_pos = disk_pos    # 在磁盘上的位置

class DynamicPaging:
    """动态分页管理类"""
    def __init__(self, memory_size=64, page_size=1, max_job_size=64):
        self.memory_size = memory_size * 1024  # 内存大小 (KB)
        self.page_size = page_size * 1024      # 页面大小 (KB)
        self.max_job_size = max_job_size * 1024  # 作业最大大小 (KB)
        
        self.total_frames = self.memory_size // self.page_size  # 总内存块数
        self.frames = [None] * self.total_frames  # 内存块使用情况
        
        self.current_job = None  # 当前作业
        self.page_table = {}     # 页表
        self.allocated_frames = []  # 分配给当前作业的内存块
        self.frame_queue = []    # FIFO队列，用于页面置换
    
    def create_job(self, job_id, job_size, allocated_frames_count):
        """创建新作业"""
        if job_size > self.max_job_size:
            return False, f"作业大小超过最大限制 {self.max_job_size/1024}KB"
        
        if allocated_frames_count > self.total_frames:
            return False, f"分配的内存块数超过总内存块数 {self.total_frames}"
        
        # 计算作业的页数
        pages_count = (job_size + self.page_size - 1) // self.page_size
        
        # 初始化页表
        self.page_table = {}
        for i in range(pages_count):
            disk_pos = f"{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(0, 9)}"
            self.page_table[i] = Page(i, False, None, False, disk_pos)
        
        # 分配内存块
        self.allocated_frames = []
        free_frames = [i for i, frame in enumerate(self.frames) if frame is None]
        
        if len(free_frames) < allocated_frames_count:
            return False, "内存不足，无法为作业分配足够的内存块"
        
        for i in range(allocated_frames_count):
            frame_no = free_frames[i]
            self.allocated_frames.append(frame_no)
            
        self.current_job = {
            "id": job_id,
            "size": job_size,
            "pages_count": pages_count,
            "allocated_frames_count": allocated_frames_count
        }
        
        self.frame_queue = []  # 重置FIFO队列
        
        return True, f"成功创建作业 {job_id}，分配 {allocated_frames_count} 个内存块"
    
    def access_memory(self, page_no, offset, operation):
        """访问内存，返回物理地址和是否缺页"""
        if page_no not in self.page_table:
            return None, False, f"页号 {page_no} 超出范围"
        
        page = self.page_table[page_no]
        
        # 如果页面不在内存中，需要调入
        if not page.exists:
            frame_no, replaced_page = self._handle_page_fault(page_no)
            if frame_no is None:
                return None, True, "无法调入页面，内存已满且无法置换"
                
            page.exists = True
            page.frame_no = frame_no
            
            # 如果是写操作，设置修改标志
            if operation in ["save", "存"]:
                page.modified = True
                
            return (frame_no * self.page_size + offset), True, replaced_page
            
        else:
            # 如果是写操作，设置修改标志
            if operation in ["save", "存"]:
                page.modified = True
                
            return (page.frame_no * self.page_size + offset), False, None
    
    def _handle_page_fault(self, page_no):
        """处理缺页中断"""
        # 检查是否有空闲的内存块
        free_frames = [frame for frame in self.allocated_frames if self.frames[frame] is None]
        
        if free_frames:
            # 有空闲内存块，直接分配
            frame_no = free_frames[0]
            self.frames[frame_no] = page_no
            self.frame_queue.append(frame_no)
            return frame_no, None
        else:
            # 无空闲内存块，需要进行页面置换
            if not self.frame_queue:
                return None, "FIFO队列为空，无法进行页面置换"
                
            # 使用FIFO算法选择要置换的页面
            replaced_frame = self.frame_queue.pop(0)
            replaced_page_no = self.frames[replaced_frame]
            
            # 更新被置换页面的状态
            if replaced_page_no is not None:
                replaced_page = self.page_table[replaced_page_no]
                replaced_page.exists = False
                replaced_page.frame_no = None
                
                # 构建被置换页面的信息
                replaced_info = f"淘汰第{replaced_page_no}页"
            else:
                replaced_info = "无需淘汰页面"
            
            # 分配内存块给新页面
            self.frames[replaced_frame] = page_no
            self.frame_queue.append(replaced_frame)
            
            return replaced_frame, replaced_info

class MemoryManagementApp:
    """内存管理模拟应用"""
    def __init__(self, root):
        self.root = root
        self.root.title("内存管理模拟系统")
        self.root.geometry("1200x700")
        
        # 先初始化管理器
        self.partition_manager = DynamicPartition(1024)
        self.paging_manager = DynamicPaging(64, 1, 64)
        
        # 创建标签页
        self.tab_control = ttk.Notebook(self.root)
        
        # 动态分区管理标签页
        self.partition_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.partition_tab, text="动态分区管理")
        self._setup_partition_tab()
        
        # 动态分页管理标签页
        self.paging_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.paging_tab, text="动态分页管理")
        self._setup_paging_tab()
        
        self.tab_control.pack(expand=1, fill="both")
        
    def _setup_partition_tab(self):
        """设置动态分区管理标签页"""
        # 创建框架
        control_frame = ttk.LabelFrame(self.partition_tab, text="控制面板")
        control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nw")
        
        info_frame = ttk.LabelFrame(self.partition_tab, text="内存状态")
        info_frame.grid(row=0, column=1, padx=10, pady=10, sticky="ne")
        
        # 控制面板内容
        ttk.Label(control_frame, text="进程ID:").grid(row=0, column=0, padx=5, pady=5)
        self.pid_entry = ttk.Entry(control_frame, width=10)
        self.pid_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(control_frame, text="内存大小:").grid(row=1, column=0, padx=5, pady=5)
        self.memory_size_entry = ttk.Entry(control_frame, width=10)
        self.memory_size_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(control_frame, text="分配算法:").grid(row=2, column=0, padx=5, pady=5)
        self.algorithm_var = tk.StringVar()
        algorithms = [("最先适应", "first_fit"), ("最佳适应", "best_fit"), ("最坏适应", "worst_fit")]
        for i, (text, value) in enumerate(algorithms):
            ttk.Radiobutton(control_frame, text=text, value=value, variable=self.algorithm_var).grid(
                row=2, column=i+1, padx=5, pady=5
            )
        self.algorithm_var.set("first_fit")
        
        allocate_btn = ttk.Button(control_frame, text="分配内存", command=self._allocate_memory)
        allocate_btn.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
        deallocate_btn = ttk.Button(control_frame, text="释放内存", command=self._deallocate_memory)
        deallocate_btn.grid(row=3, column=2, columnspan=2, padx=5, pady=5)
        
        # 内存状态显示
        self.memory_status_text = scrolledtext.ScrolledText(info_frame, width=60, height=20)
        self.memory_status_text.pack(padx=10, pady=10)
        
        # 操作日志
        log_frame = ttk.LabelFrame(self.partition_tab, text="操作日志")
        log_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, width=80, height=10)
        self.log_text.pack(padx=10, pady=10, fill="both", expand=True)
        
        # 视觉化显示
        visual_frame = ttk.LabelFrame(self.partition_tab, text="内存可视化")
        visual_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        
        self.canvas = tk.Canvas(visual_frame, width=1000, height=100, bg="white")
        self.canvas.pack(padx=10, pady=10)
        
        # 更新内存状态显示
        self._update_partition_display()
        
    def _setup_paging_tab(self):
        """设置动态分页管理标签页"""
        # 创建框架
        control_frame = ttk.LabelFrame(self.paging_tab, text="作业控制")
        control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nw")
        
        operation_frame = ttk.LabelFrame(self.paging_tab, text="指令操作")
        operation_frame.grid(row=0, column=1, padx=10, pady=10, sticky="ne")
        
        # 作业控制面板
        ttk.Label(control_frame, text="作业ID:").grid(row=0, column=0, padx=5, pady=5)
        self.job_id_entry = ttk.Entry(control_frame, width=10)
        self.job_id_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(control_frame, text="作业大小(KB):").grid(row=1, column=0, padx=5, pady=5)
        self.job_size_entry = ttk.Entry(control_frame, width=10)
        self.job_size_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(control_frame, text="分配内存块数:").grid(row=2, column=0, padx=5, pady=5)
        self.allocated_frames_entry = ttk.Entry(control_frame, width=10)
        self.allocated_frames_entry.grid(row=2, column=1, padx=5, pady=5)
        
        create_job_btn = ttk.Button(control_frame, text="创建作业", command=self._create_job)
        create_job_btn.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
        # 指令操作面板
        ttk.Label(operation_frame, text="操作:").grid(row=0, column=0, padx=5, pady=5)
        self.operation_var = tk.StringVar()
        operations = [("+", "+"), ("-", "-"), ("×", "×"), ("/", "/"), ("存", "save"), ("取", "load")]
        for i, (text, value) in enumerate(operations):
            ttk.Radiobutton(operation_frame, text=text, value=value, variable=self.operation_var).grid(
                row=0, column=i+1, padx=5, pady=5
            )
        self.operation_var.set("+")
        
        ttk.Label(operation_frame, text="页号:").grid(row=1, column=0, padx=5, pady=5)
        self.page_no_entry = ttk.Entry(operation_frame, width=10)
        self.page_no_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(operation_frame, text="页内偏移:").grid(row=2, column=0, padx=5, pady=5)
        self.offset_entry = ttk.Entry(operation_frame, width=10)
        self.offset_entry.grid(row=2, column=1, padx=5, pady=5)
        
        execute_btn = ttk.Button(operation_frame, text="执行指令", command=self._execute_instruction)
        execute_btn.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
        # 页表和访问日志显示
        display_frame = ttk.Frame(self.paging_tab)
        display_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        
        page_table_frame = ttk.LabelFrame(display_frame, text="页表")
        page_table_frame.pack(side=tk.LEFT, padx=5, pady=5, fill="both", expand=True)
        
        self.page_table_text = scrolledtext.ScrolledText(page_table_frame, width=40, height=15)
        self.page_table_text.pack(padx=5, pady=5, fill="both", expand=True)
        
        access_log_frame = ttk.LabelFrame(display_frame, text="访问日志")
        access_log_frame.pack(side=tk.RIGHT, padx=5, pady=5, fill="both", expand=True)
        
        self.access_log_text = scrolledtext.ScrolledText(access_log_frame, width=40, height=15)
        self.access_log_text.pack(padx=5, pady=5, fill="both", expand=True)
        
        # 内存状态可视化
        visual_frame = ttk.LabelFrame(self.paging_tab, text="内存状态可视化")
        visual_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        
        self.paging_canvas = tk.Canvas(visual_frame, width=1000, height=100, bg="white")
        self.paging_canvas.pack(padx=10, pady=10, fill="both", expand=True)
    
    def _allocate_memory(self):
        """分配内存"""
        try:
            pid = int(self.pid_entry.get())
            memory_size = int(self.memory_size_entry.get())
            algorithm = self.algorithm_var.get()
            
            if memory_size <= 0:
                messagebox.showerror("错误", "内存大小必须为正数")
                return
                
            process = Process(pid, memory_size)
            success, message = self.partition_manager.allocate(process, algorithm)
            
            self._log_message(message)
            self._update_partition_display()
            
            if not success:
                messagebox.showwarning("分配失败", message)
                
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的进程ID和内存大小")
    
    def _deallocate_memory(self):
        """释放内存"""
        try:
            pid = int(self.pid_entry.get())
            
            success, message = self.partition_manager.deallocate(pid)
            
            self._log_message(message)
            self._update_partition_display()
            
            if not success:
                messagebox.showwarning("释放失败", message)
                
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的进程ID")
    
    def _update_partition_display(self):
        """更新分区显示"""
        # 更新文本区域
        self.memory_status_text.delete(1.0, tk.END)
        
        memory_status = self.partition_manager.get_memory_status()
        for i, block in enumerate(memory_status):
            self.memory_status_text.insert(tk.END, f"{i+1}. {block}\n")
        
        # 更新可视化显示
        self.canvas.delete("all")
        
        total_width = 1000
        total_memory = self.partition_manager.memory_size
        
        x_pos = 0
        for block in self.partition_manager.memory_blocks:
            block_width = (block.size / total_memory) * total_width
            
            # 根据是否分配设置颜色
            if block.allocated:
                color = f"#{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(0, 9)}"
                text = f"P{block.process_id}"
            else:
                color = "white"
                text = "空闲"
                
            # 绘制矩形
            self.canvas.create_rectangle(x_pos, 10, x_pos + block_width, 90, 
                                        fill=color, outline="black")
            
            # 添加文本
            self.canvas.create_text(x_pos + block_width/2, 50, 
                                   text=f"{text}\n{block.size}B", font=("Arial", 9))
            
            # 添加起始地址
            self.canvas.create_text(x_pos + 5, 5, text=str(block.start_addr), 
                                   anchor=tk.W, font=("Arial", 8))
            
            x_pos += block_width
    
    def _log_message(self, message):
        """记录日志消息"""
        current_time = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{current_time}] {message}\n")
        self.log_text.see(tk.END)
    
    def _create_job(self):
        """创建作业"""
        try:
            job_id = self.job_id_entry.get()
            job_size = int(self.job_size_entry.get())
            allocated_frames = int(self.allocated_frames_entry.get())
            
            success, message = self.paging_manager.create_job(job_id, job_size * 1024, allocated_frames)
            
            if success:
                messagebox.showinfo("成功", message)
                self._update_page_table_display()
                self._update_paging_display()
            else:
                messagebox.showwarning("失败", message)
                
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的作业大小和内存块数")
    
    def _execute_instruction(self):
        """执行指令"""
        if not self.paging_manager.current_job:
            messagebox.showwarning("错误", "请先创建作业")
            return
            
        try:
            operation = self.operation_var.get()
            page_no = int(self.page_no_entry.get())
            offset = int(self.offset_entry.get())
            
            if offset >= self.paging_manager.page_size:
                messagebox.showwarning("错误", f"页内偏移超出范围 (0-{self.paging_manager.page_size-1})")
                return
                
            physical_addr, page_fault, info = self.paging_manager.access_memory(page_no, offset, operation)
            
            if physical_addr is not None:
                fault_status = "发生缺页中断，" + info if page_fault else "不缺页"
                log_message = f"指令: {operation} {page_no} {offset}, 物理地址: {physical_addr}, {fault_status}"
                
                self.access_log_text.insert(tk.END, log_message + "\n")
                self.access_log_text.see(tk.END)
                
                self._update_page_table_display()
                self._update_paging_display()
            else:
                messagebox.showwarning("错误", info)
                
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的页号和页内偏移")
    
    def _update_page_table_display(self):
        """更新页表显示"""
        self.page_table_text.delete(1.0, tk.END)
        
        self.page_table_text.insert(tk.END, "页号\t标志\t内存块号\t修改标志\t磁盘位置\n")
        self.page_table_text.insert(tk.END, "-" * 50 + "\n")
        
        for page_no, page in self.paging_manager.page_table.items():
            exists = "1" if page.exists else "0"
            frame_no = page.frame_no if page.exists else " "
            modified = "1" if page.modified else "0"
            
            self.page_table_text.insert(tk.END, 
                f"{page_no}\t{exists}\t{frame_no}\t{modified}\t{page.disk_pos}\n")
    
    def _update_paging_display(self):
        """更新分页内存状态可视化"""
        self.paging_canvas.delete("all")
        
        frame_width = 50
        frame_height = 80
        
        # 绘制内存块
        for i in range(self.paging_manager.total_frames):
            x = (i % 20) * frame_width + 10
            y = (i // 20) * frame_height + 10
            
            # 判断是否是分配给当前作业的内存块
            is_allocated = i in self.paging_manager.allocated_frames
            
            # 根据内存块状态设置颜色
            if is_allocated:
                if self.paging_manager.frames[i] is not None:
                    # 内存块已被使用
                    color = "#4CAF50"  # 绿色
                    page_no = self.paging_manager.frames[i]
                    text = f"页{page_no}"
                else:
                    # 内存块已分配但未使用
                    color = "#FFC107"  # 黄色
                    text = "空闲"
            else:
                # 不属于当前作业的内存块
                color = "#E0E0E0"  # 灰色
                text = ""
                
            self.paging_canvas.create_rectangle(x, y, x + frame_width, y + frame_height,
                                              fill=color, outline="black")
            
            # 添加内存块号
            self.paging_canvas.create_text(x + 5, y + 5, text=f"{i}", anchor=tk.NW, font=("Arial", 8))
            
            # 添加页号
            self.paging_canvas.create_text(x + frame_width/2, y + frame_height/2, 
                                         text=text, font=("Arial", 9))

if __name__ == "__main__":
    root = tk.Tk()
    app = MemoryManagementApp(root)
    root.mainloop()
