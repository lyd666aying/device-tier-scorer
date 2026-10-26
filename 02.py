"""演示入口：跑一批样例设备，输出评分与各场景推荐配置。

用法：
    python demo.py                 # 打印全部样例
    python demo.py --json          # 输出 JSON（便于二次处理）
    python demo.py --profile pc-ai # 只跑指定 profile
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Windows 控制台默认 GBK，直接 print 中文可能抛 UnicodeEncodeError 或输出乱码
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, str(Path(__file__).parent))

from devtier import DeviceSpec, apply_profile, list_profiles, score_device  # noqa: E402

SAMPLES = [
    {
        "label": "小米 15（旗舰安卓）",
        "spec": DeviceSpec(platform="android", brand="Xiaomi", model="15",
                           soc="Snapdragon 8 Elite", cpu_cores=8,
                           cpu_max_freq_mhz=4320, process_nm=3, ram_mb=12288),
    },
    {
        "label": "未知安卓机（只有硬件参数）",
        "spec": DeviceSpec(platform="android", cpu_cores=8, cpu_max_freq_mhz=2200,
                           process_nm=14, ram_mb=4096),
    },
    {
        "label": "iPhone 11",
        "spec": DeviceSpec(platform="ios", brand="Apple", model="iPhone 11",
                           ram_mb=4096),
    },
    {
        "label": "未命中机型库的 iOS 设备",
        "spec": DeviceSpec(platform="ios", cpu_cores=6, cpu_max_freq_mhz=2650,
                           process_nm=7, ram_mb=4096),
    },
    {
        "label": "RTX 5050 笔记本（8GB 显存）",
        "spec": DeviceSpec(platform="windows", gpu="RTX 5050", vram_mb=8192,
                           ram_mb=16384),
    },
    {
        "label": "RTX 4090 工作站（24GB 显存）",
        "spec": DeviceSpec(platform="windows", gpu="RTX 4090", vram_mb=24576,
                           ram_mb=65536),
    },
    {
        "label": "未识别 GPU 的桌面机",
        "spec": DeviceSpec(platform="windows", vram_mb=6144, ram_mb=16384),
    },
]

PROFILE_FOR_PLATFORM = {
    "android": "mobile-live",
    "ios": "mobile-live",
    "windows": "pc-ai",
    "linux": "pc-ai",
    "macos": "pc-ai",
}

LINE = "=" * 66
SUB = "-" * 66


def render_text(results, only_profile=None):
    out = [LINE, "devtier - 设备能力分级与自适应配置推荐引擎", "可用 profile: " +
           ", ".join("%s(%s)" % (k, v) for k, v in list_profiles().items()), LINE]

    for item in results:
        label, result = item["label"], item["result"]
        out.append("")
        out.append("[%s]  platform=%s" % (label, result.spec.platform))
        if result.spec.model or result.spec.gpu:
            out.append("       设备标识=%s" % (result.spec.model or result.spec.gpu))
        out.append(SUB)
        out.append("  评分 %d / 50      档位 %s" % (result.score, result.tier))
        out.append("  判定来源：%s" % result.source_label)
        if result.matched_key:
            out.append("  命中键：%s" % result.matched_key)
        if result.components:
            comp = "  ".join("%s=%s" % (k, v) for k, v in result.components.items())
            out.append("  评分构成：%s" % comp)
        for note in result.notes:
            out.append("  · %s" % note)

        pname = only_profile or PROFILE_FOR_PLATFORM.get(result.spec.platform)
        if not pname:
            continue
        pr = apply_profile(result, pname)
        out.append(SUB)
        out.append("  profile: %s    tier: %s" % (pr.profile, pr.tier))
        if pr.config:
            keys = [
                ("vram_gb", "显存(GB)"), ("deployable", "可否部署"),
                ("max_params_b", "建议模型上限(B)"), ("quant", "量化"),
                ("weights_gb", "权重占用(GB)"), ("max_ctx", "建议上下文"),
                ("batch_size", "批大小"),
                ("resolution", "分辨率"), ("fps", "帧率"),
                ("bitrate_kbps", "码率(kbps)"), ("beauty_level_name", "美颜档位"),
                ("beauty_items", "美颜项"), ("max_concurrent_effects", "并发特效数"),
            ]
            for key, cn in keys:
                if key in pr.config:
                    out.append("    %-14s: %s" % (cn, pr.config[key]))
            if pr.fallback_ladder:
                out.append("    %-14s: %s" % ("降级阶梯", " -> ".join(pr.fallback_ladder)))
        for a in pr.advice:
            out.append("    · %s" % a)

    out.append("")
    out.append(LINE)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="devtier 演示")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    ap.add_argument("--profile", default=None, help="只应用指定 profile")
    args = ap.parse_args()

    results = []
    for s in SAMPLES:
        results.append({"label": s["label"], "result": score_device(s["spec"])})

    if args.json:
        payload = []
        for item in results:
            r = item["result"]
            entry = {"label": item["label"], "score": r.to_dict()}
            pname = args.profile or PROFILE_FOR_PLATFORM.get(r.spec.platform)
            if pname:
                entry["profile"] = apply_profile(r, pname).to_dict()
            payload.append(entry)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print(render_text(results, only_profile=args.profile))


if __name__ == "__main__":
    main()
