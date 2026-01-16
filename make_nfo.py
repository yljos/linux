import os
from pathlib import Path

# ================= 配置区域 =================

# 1. 扫描路径
TARGET_FOLDER = r"Z:\media\mv"

# 2. 文件夹名 -> 合集名 的映射表
FOLDER_MAPPING = {
    "Girls_Generation": "少女时代",
    "After_School": "After School 下课",
    "AOA": "AOA",
    "BILIBILI": "哔哩哔哩",
    "DALSHABET": "Dal Shabet",
    "EXID": "EXID",
    "FIESTAR": "Fiestar",
    "Fourladies_4_Light": "Four Ladies 4Light",
    "GAINA": "G.NA",
    "Girl_Crush": "Girl Crush",
    "Gong_Yue_Fei": "龚玥菲",
    "Hello_Venus": "Hello Venus",
    "HYUNA": "泫雅",
    "Idance_Studio": "iDance Studio",
    "LAYSHA": "LAYSHA",
    "Liu_Yi_Fei": "刘亦菲",
    "MMD": "MMD",
    "MOMOLAND": "MOMOLAND",
    "Nine_Muses": "Nine Muses 九Muses",
    "Ns_Yoon_G": "NS Yoon-G",
    "Pao_Fu_Mao": "泡芙猫",
    "Rainbow_Blaxx": "Rainbow Blaxx",
    "SECRET": "SECRET",
    "SISTAR": "SISTAR",
    "Song_Jieun": "宋智恩",
    "STELLAR": "STELLAR",
    "TARA": "T-ARA",
    "Wonder_Girls": "Wonder Girls",
    "Xia_Zhen": "夏真",
    "Yi_Neng_Jing": "伊能静",
    "Yu_Shan_Shan": "鱼闪闪",
    "Z_N_K_K": "甄妮可可",
}

# 3. 视频文件的后缀名 (严格按照您的要求，仅限 mp4 和 webm)
VIDEO_EXTS = [".mp4", ".webm"]

# 4. 是否覆盖已存在的 NFO 文件？
OVERWRITE = True

# ================= 脚本逻辑 =================


def generate_nfo():
    root_folder = Path(TARGET_FOLDER)

    if not root_folder.exists():
        print(f"❌ 错误：找不到路径 {TARGET_FOLDER}")
        print("   请确认 Z: 盘已挂载且路径正确。")
        return

    print(f"📂 正在递归扫描目录: {TARGET_FOLDER}")
    print(f"📋 加载映射配置: {len(FOLDER_MAPPING)} 个规则")

    count = 0

    # rglob('*') 会递归遍历所有子目录下的所有文件
    for file_path in root_folder.rglob("*"):

        # 1. 基础检查：是文件 且 后缀匹配
        if file_path.is_file() and file_path.suffix.lower() in VIDEO_EXTS:

            # 2. 获取当前视频所在的文件夹名字
            parent_folder_name = file_path.parent.name

            # 3. 决定合集名称
            collection_name = FOLDER_MAPPING.get(parent_folder_name, parent_folder_name)

            # 4. 生成 NFO 路径
            nfo_path = file_path.with_suffix(".nfo")

            # 5. 检查是否跳过
            if nfo_path.exists() and not OVERWRITE:
                print(f"⏭️  跳过 (已存在): {file_path.parent.name}/{nfo_path.name}")
                continue

            # 6. 获取视频标题 (文件名不带后缀)
            title = file_path.stem

            # 7. 构建 XML 内容
            nfo_content = (
                "<movie>\n"
                f"  <title>{title}</title>\n"
                f"  <set>{collection_name}</set>\n"
                "</movie>"
            )

            try:
                with open(nfo_path, "w", encoding="utf-8") as f:
                    f.write(nfo_content)
                print(f"✅ [{collection_name}] 生成: {file_path.name}")
                count += 1
            except Exception as e:
                print(f"❌ 写入失败 {file_path.name}: {e}")

    print("-" * 30)
    print(f"🎉 处理完成！共生成了 {count} 个 NFO 文件。")
    input("按回车键退出...")


if __name__ == "__main__":
    generate_nfo()
