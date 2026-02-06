# -*- coding: utf-8 -*-
import os
import sys
import re
import struct
import hashlib
import zlib  # SVGA 2.0 核心依赖
from typing import List, Tuple, Optional, Dict

# ==============================================================================
# SECTION 1: 动态构建 SVGA Protobuf 定义 (SVGA 2.0 标准版)
# ==============================================================================
from google.protobuf import descriptor_pb2
from google.protobuf import message_factory

def build_svga_classes():
    """
    使用代码动态生成 Protobuf 消息类。
    结构严格遵循 SVGA 2.0 定义。
    """
    # 1. 创建文件描述符
    fd_proto = descriptor_pb2.FileDescriptorProto()
    fd_proto.name = 'svga.proto'
    fd_proto.package = 'com.opensource.svga'
    fd_proto.syntax = 'proto2' 

    # 辅助函数：添加字段
    def add_field(msg, name, number, type_enum, label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL, type_name=None):
        f = msg.field.add()
        f.name = name
        f.number = number
        f.type = type_enum
        f.label = label
        if type_name: f.type_name = type_name

    # --- MovieParams ---
    mp = fd_proto.message_type.add()
    mp.name = 'MovieParams'
    add_field(mp, 'viewBoxWidth', 1, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)
    add_field(mp, 'viewBoxHeight', 2, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)
    add_field(mp, 'fps', 3, descriptor_pb2.FieldDescriptorProto.TYPE_INT32)
    add_field(mp, 'frames', 4, descriptor_pb2.FieldDescriptorProto.TYPE_INT32)
    add_field(mp, 'version', 5, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)

    # --- Layout ---
    layout = fd_proto.message_type.add()
    layout.name = 'Layout'
    add_field(layout, 'x', 1, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)
    add_field(layout, 'y', 2, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)
    add_field(layout, 'width', 3, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)
    add_field(layout, 'height', 4, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)

    # --- Transform ---
    tf = fd_proto.message_type.add()
    tf.name = 'Transform'
    add_field(tf, 'a', 1, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)
    add_field(tf, 'b', 2, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)
    add_field(tf, 'c', 3, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)
    add_field(tf, 'd', 4, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)
    add_field(tf, 'tx', 5, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)
    add_field(tf, 'ty', 6, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)

    # --- ShapeEntity (占位) ---
    sh = fd_proto.message_type.add()
    sh.name = 'ShapeEntity'

    # --- FrameEntity ---
    fe = fd_proto.message_type.add()
    fe.name = 'FrameEntity'
    add_field(fe, 'alpha', 1, descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT)
    add_field(fe, 'layout', 2, descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE, type_name='.com.opensource.svga.Layout')
    add_field(fe, 'transform', 3, descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE, type_name='.com.opensource.svga.Transform')
    # repeated ShapeEntity
    add_field(fe, 'shapes', 5, descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE, 
              label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED, type_name='.com.opensource.svga.ShapeEntity')

    # --- SpriteEntity ---
    se = fd_proto.message_type.add()
    se.name = 'SpriteEntity'
    add_field(se, 'imageKey', 1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    # repeated FrameEntity
    add_field(se, 'frames', 2, descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE, 
              label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED, type_name='.com.opensource.svga.FrameEntity')

    # --- MovieEntity ---
    me = fd_proto.message_type.add()
    me.name = 'MovieEntity'
    # 严格顺序: version(1), params(2), images(3), sprites(4)
    add_field(me, 'version', 1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(me, 'params', 2, descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE, type_name='.com.opensource.svga.MovieParams')
    
    # Map<string, bytes> images
    img_entry = me.nested_type.add()
    img_entry.name = 'ImagesEntry'
    img_entry.options.map_entry = True
    add_field(img_entry, 'key', 1, descriptor_pb2.FieldDescriptorProto.TYPE_STRING)
    add_field(img_entry, 'value', 2, descriptor_pb2.FieldDescriptorProto.TYPE_BYTES)

    add_field(me, 'images', 3, descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE, 
              label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED, type_name='.com.opensource.svga.MovieEntity.ImagesEntry')
    
    add_field(me, 'sprites', 4, descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE, 
              label=descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED, type_name='.com.opensource.svga.SpriteEntity')

    messages = message_factory.GetMessages([fd_proto])
    return messages['com.opensource.svga.MovieEntity']

# 初始化 SVGA 类
try:
    MovieEntity = build_svga_classes()
except Exception as e:
    print(f"Protobuf 初始化失败: {e}")
    sys.exit(1)

# ==============================================================================
# SECTION 2: 工具类
# ==============================================================================

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_err(msg):
    print(f"{Colors.FAIL}[Error] {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKBLUE}[Info] {msg}{Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.OKGREEN}[Success] {msg}{Colors.ENDC}")

def print_warn(msg):
    print(f"{Colors.WARNING}[Warning] {msg}{Colors.ENDC}")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_png_info(file_path: str) -> Tuple[Optional[int], Optional[int], bool]:
    try:
        with open(file_path, 'rb') as f:
            signature = f.read(8)
            if signature != b'\x89PNG\r\n\x1a\n':
                return None, None, False
            f.seek(16)
            ihdr_data = f.read(13)
            if len(ihdr_data) < 13:
                return None, None, False
            w, h, bit_depth, color_type = struct.unpack('>IIBB', ihdr_data[:10])
            is_rgba = (color_type == 6)
            return w, h, is_rgba
    except Exception:
        return None, None, False

# ==============================================================================
# SECTION 3: 主逻辑
# ==============================================================================

class SVGAConverter:
    def __init__(self):
        self.src_dir = ""
        self.target_count = 0
        self.fps = 0
        self.width = 0
        self.height = 0
        self.out_dir = ""
        self.prefix = ""
        self.suffix = ""
        
    def get_user_input(self):
        print(f"{Colors.HEADER}=== SVGA Builder 2.0 (Native Zlib Binary) ==={Colors.ENDC}")
        print("请依次输入以下信息：")
        
        # 1. 源文件夹
        while True:
            path = input(f"{Colors.BOLD}1. 原始PNG文件夹路径: {Colors.ENDC}").strip()
            path = path.strip('"').strip("'")
            if os.path.isdir(path):
                self.src_dir = path
                break
            print_err("路径不存在或不是文件夹，请重试。")
            
        # 2. 数量
        while True:
            try:
                cnt_str = input(f"{Colors.BOLD}2. 原始PNG文件数量: {Colors.ENDC}").strip()
                cnt = int(cnt_str)
                if cnt > 0:
                    self.target_count = cnt
                    break
                print_err("数量必须大于0")
            except ValueError:
                print_err("请输入有效的数字")

        # 3. 帧率
        while True:
            try:
                fps_str = input(f"{Colors.BOLD}3. 目标帧率 (建议 20-60): {Colors.ENDC}").strip()
                fps = int(fps_str)
                if fps > 0:
                    self.fps = fps
                    break
                print_err("帧率必须大于0")
            except ValueError:
                print_err("请输入有效的数字")
                
        # 4. 分辨率
        while True:
            try:
                w_str = input(f"{Colors.BOLD}4.1 目标宽度 (px): {Colors.ENDC}").strip()
                w = int(w_str)
                h_str = input(f"{Colors.BOLD}4.2 目标高度 (px): {Colors.ENDC}").strip()
                h = int(h_str)
                if w > 0 and h > 0:
                    self.width = w
                    self.height = h
                    break
                print_err("宽高必须大于0")
            except ValueError:
                print_err("请输入有效的数字")

        # 5. 导出路径
        while True:
            path = input(f"{Colors.BOLD}5. 导出文件夹路径: {Colors.ENDC}").strip()
            path = path.strip('"').strip("'")
            if not os.path.exists(path):
                try:
                    os.makedirs(path)
                    self.out_dir = path
                    break
                except Exception as e:
                    print_err(f"无法创建文件夹: {e}")
            elif os.path.isdir(path):
                self.out_dir = path
                break
            else:
                print_err("路径存在但不是文件夹。")

        # 6. 文件名格式
        print(f"{Colors.WARNING}文件名格式示例: 如 frame_0001.png，前缀为'frame_'，后缀为'' (如有后缀需填){Colors.ENDC}")
        self.prefix = input(f"{Colors.BOLD}6.1 可选文本1 (前缀, 可留空): {Colors.ENDC}")
        self.suffix = input(f"{Colors.BOLD}6.2 可选文本2 (后缀, 不含.png, 可留空): {Colors.ENDC}")

    def confirm_info(self) -> bool:
        print("\n" + "="*40)
        print(f"{Colors.HEADER}任务信息确认:{Colors.ENDC}")
        print(f"源目录:   {self.src_dir}")
        print(f"文件总量: {self.target_count}")
        print(f"FPS:      {self.fps}")
        print(f"分辨率:   {self.width} x {self.height}")
        print(f"导出目录: {self.out_dir}")
        print(f"命名格式: {self.prefix}[数字]{self.suffix}.png")
        print("="*40)
        
        while True:
            ans = input(f"{Colors.WARNING}是否开始处理? (y/n): {Colors.ENDC}").lower().strip()
            if ans == 'y': return True
            if ans == 'n': return False

    def validate_and_sort_files(self) -> List[str]:
        print_info("正在扫描并校验文件...")
        
        escaped_prefix = re.escape(self.prefix)
        escaped_suffix = re.escape(self.suffix)
        pattern_str = f"^{escaped_prefix}(\\d+){escaped_suffix}\\.png$"
        regex = re.compile(pattern_str, re.IGNORECASE)
        
        valid_files = []
        
        try:
            files_in_dir = os.listdir(self.src_dir)
        except Exception as e:
            raise Exception(f"读取文件夹失败: {e}")

        for fname in files_in_dir:
            match = regex.match(fname)
            if match:
                num_str = match.group(1)
                full_path = os.path.join(self.src_dir, fname)
                valid_files.append({
                    "num": int(num_str),
                    "path": full_path,
                    "name": fname
                })
        
        # 排序
        valid_files.sort(key=lambda x: x["num"])
        
        if len(valid_files) != self.target_count:
            raise Exception(f"文件匹配数量不一致！找到 {len(valid_files)} 个符合格式的文件，但要求 {self.target_count} 个。")
            
        first_file = valid_files[0]["path"]
        print_info(f"正在检测首帧: {valid_files[0]['name']}")
        
        w, h, is_rgba = get_png_info(first_file)
        
        if w is None:
            raise Exception("首帧不是有效的 PNG 文件或无法读取头信息。")
            
        if w != self.width or h != self.height:
            raise Exception(f"尺寸不匹配！首帧尺寸为 {w}x{h}，但目标设置为 {self.width}x{self.height}。")
            
        if not is_rgba:
             print_warn("检测到首帧似乎没有 Alpha 通道 (非 RGBA)，可能导致背景不透明。")

        return [x["path"] for x in valid_files]

    def build_svga(self, file_paths: List[str]):
        print_info("开始构建 SVGA 数据结构 (Binary Mode)...")
        
        movie = MovieEntity()
        movie.version = "2.0" 
        movie.params.viewBoxWidth = float(self.width)
        movie.params.viewBoxHeight = float(self.height)
        movie.params.fps = self.fps
        movie.params.frames = self.target_count
        
        md5_to_key = {}
        frames_keys = []
        
        print_info("读取并嵌入图片数据...")
        
        for idx, fpath in enumerate(file_paths):
            if idx % 10 == 0:
                print(f"\r进度: {idx+1}/{self.target_count}", end="")
            
            with open(fpath, 'rb') as f:
                raw_bytes = f.read()
            
            # 使用 Hash 去重
            file_hash = hashlib.md5(raw_bytes).hexdigest()
            
            if file_hash in md5_to_key:
                frame_key = md5_to_key[file_hash]
            else:
                frame_key = f"img_{file_hash[:10]}" 
                md5_to_key[file_hash] = frame_key
                # 【核心逻辑回归】: 直接存入 bytes
                movie.images[frame_key] = raw_bytes 
            
            frames_keys.append(frame_key)
            
        print("\n正在生成 Sprites (序列帧布局)...")
        
        # 序列帧逻辑
        key_usage = {}
        for idx, key in enumerate(frames_keys):
            if key not in key_usage:
                key_usage[key] = []
            key_usage[key].append(idx)
            
        for key, active_frames in key_usage.items():
            sprite = movie.sprites.add()
            sprite.imageKey = key 
            
            for f_i in range(self.target_count):
                frame = sprite.frames.add()
                frame.layout.x = 0
                frame.layout.y = 0
                frame.layout.width = float(self.width)
                frame.layout.height = float(self.height)
                
                # 显式初始化 Transform
                frame.transform.a = 1.0
                frame.transform.b = 0.0
                frame.transform.c = 0.0
                frame.transform.d = 1.0
                frame.transform.tx = 0.0
                frame.transform.ty = 0.0
                
                if f_i in active_frames:
                    frame.alpha = 1.0
                else:
                    frame.alpha = 0.0
        
        print(f"\n构建完成：共 {len(movie.sprites)} 个 Sprite 图层。")
        return movie

    def save_file(self, movie_entity):
        # 【关键修改】: Protobuf Serialize + Zlib Compress
        print_info("正在序列化 Protobuf 数据...")
        raw_data = movie_entity.SerializeToString()
        
        print_info(f"正在进行 Zlib 全文压缩 (Raw size: {len(raw_data)/1024/1024:.2f} MB)...")
        try:
            compressed_data = zlib.compress(raw_data, level=9) # 使用最高压缩等级
        except Exception as e:
            print_err(f"压缩失败: {e}")
            return

        folder_name = os.path.basename(os.path.normpath(self.src_dir))
        if not folder_name:
            folder_name = "output"
        out_filename = f"{folder_name}.svga"
        out_path = os.path.join(self.out_dir, out_filename)
        
        try:
            with open(out_path, 'wb') as f:
                f.write(compressed_data)
                    
            print_success(f"导出成功: {out_path}")
            print(f"最终文件大小: {os.path.getsize(out_path) / 1024 / 1024 :.2f} MB")
        except Exception as e:
            print_err(f"保存文件失败: {e}")

    def run(self):
        while True:
            clear_screen()
            self.get_user_input()
            
            if not self.confirm_info():
                continue
                
            try:
                file_list = self.validate_and_sort_files()
                movie_obj = self.build_svga(file_list)
                self.save_file(movie_obj)
                
                input(f"\n{Colors.OKGREEN}按回车键退出，或按 Ctrl+C 终止...{Colors.ENDC}")
                break
                
            except Exception as e:
                print_err(str(e))
                input(f"\n{Colors.WARNING}按回车键重新开始...{Colors.ENDC}")
                continue

if __name__ == "__main__":
    try:
        app = SVGAConverter()
        app.run()
    except KeyboardInterrupt:
        print("\n程序已终止。")
        sys.exit(0)
