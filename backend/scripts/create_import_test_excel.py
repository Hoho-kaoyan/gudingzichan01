"""
根据当前用户导入、资产导入的字段定义，生成测试用 Excel 文件。
列定义以 backend/routers/users.py、backend/routers/assets.py 的导入逻辑为准。
资产列名兼容：实物状态/状态，具体存放楼层/存放楼层，终端IP号/IP地址，终端mac地址/MAC地址，
使用人组别/组別/组别；使用人可填 所有人ID 或 使用人EHR号（二选一）。
输出：docs/测试/用户导入测试.xlsx、docs/测试/资产导入测试.xlsx
在项目根目录执行：python3 backend/scripts/create_import_test_excel.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "docs" / "测试"
OUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    import pandas as pd
except ImportError:
    pd = None


def create_user_import_excel():
    """用户导入：必填 EHR号、姓名、组别；可选 角色、状态、密码"""
    columns = ["EHR号", "姓名", "组别", "角色", "状态", "密码"]
    data = [
        ["1000001", "测试用户一", "第1组", "user", "在岗", "123456"],
        ["1000002", "测试用户二", "管理组", "admin", "在岗", "123456"],
        ["1000003", "测试用户三", "第2组", "user", "在岗", "123456"],
    ]
    df = pd.DataFrame(data, columns=columns)
    path = OUT_DIR / "用户导入测试.xlsx"
    df.to_excel(path, index=False, sheet_name="用户")
    print(f"已生成: {path}")
    return path


def create_asset_import_excel():
    """资产导入：必填 资产编号、所属大类、实物名称；其余为可选（与后端列名及兼容列名一致）"""
    columns = [
        "资产编号",
        "所属大类",
        "实物名称",
        "规格型号",
        "件数",
        "实物状态",
        "存放办公地点",
        "具体存放楼层",
        "所有人",
        "组別",
        "所在团队",
        "终端IP号",
        "终端mac地址",
        "座位号",
        "备注说明",
        "购置日期",
        "卡片编号",
        "检查执行人",
        "电脑类型",
        "电脑应用",
        "计算机名",
        "连接显示器1型号",
        "连接显示器1资产编号",
        "显示器1序列号",
        "连接显示器2型号",
        "连接显示器2资产编号",
        "显示器2序列号",
        "资产管理联系人",
        "预留1",
        "预留2",
        "预留3",
        "预留4",
        "预留5",
        "预留6",
    ]
    data = [
        [
            "ASSET-TEST-001",
            "电子设备配件",
            "终端",
            "ThinkPad X1",
            1,
            "在用",
            "总部A座",
            "3F",
            "测试用户一",
            "第1组",
            "研发组",
            "192.168.1.101",
            "00:11:22:33:44:55",
            "A-101",
            "测试资产1",
            "2024-01-15",
            "CARD001",
            "测试用户一",
            "笔记本",
            "",
            "PC-DEV-01",
            "Dell U2720",
            "MNT001",
            "SN-M1-001",
            "Dell U2720",
            "MNT002",
            "SN-M2-001",
            "张三",
            "", "", "", "", "", "",
        ],
        [
            "ASSET-TEST-002",
            "办公用品",
            "显示器",
            "24寸/IPS",
            1,
            "在库",
            "",
            "1F",
            "",
            "",
            "",
            "",
            "",
            "",
            "待分配",
            "2024-02-01",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "", "", "", "", "", "",
        ],
        [
            "ASSET-TEST-003",
            "电子设备配件",
            "主机",
            "i5-12400",
            1,
            "在用",
            "总部B座",
            "2F",
            "测试用户二",
            "管理组",
            "运维组",
            "192.168.1.102",
            "00:AA:BB:CC:DD:EE",
            "B-202",
            "测试主机",
            "",
            "",
            "测试用户二",
            "台式机",
            "办公",
            "PC-OFFICE-02",
            "",
            "",
            "",
            "",
            "",
            "",
            "李四",
            "", "", "", "", "", "",
        ],
    ]
    df = pd.DataFrame(data, columns=columns)
    path = OUT_DIR / "资产导入测试.xlsx"
    df.to_excel(path, index=False, sheet_name="资产")
    print(f"已生成: {path}")
    return path


if __name__ == "__main__":
    if pd is None:
        print("请先安装 pandas 和 openpyxl: pip install pandas openpyxl")
        raise SystemExit(1)
    create_user_import_excel()
    create_asset_import_excel()
    print("完成。")
