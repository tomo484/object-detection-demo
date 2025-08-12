import argparse, json, csv, math, os, glob
from pathlib import Path
import cv2
import yaml
from ultralytics import YOLO

# 以下関数はeval_angle_mae.pyと同じ関数なので、後で消し、importするようにする
def angle_deg(pivot_xy, tip_xy):
    dx = tip_xy[0] - pivot_xy[0]
    dy = tip_xy[1] - pivot_xy[1]
    ang = math.degrees(math.atan2(-dy, dx))
    return (ang + 360.0) % 360.0

# 以下関数はeval_angle_mae.pyと同じ関数なので、後で消し、importするようにする
def circ_abs_diff_deg(a, b):
    return abs(((a - b + 180.0) % 360.0) - 180.0)


def map_angle_to_value(ang, cfg):
    t0 = float(cfg["theta_min"])
    t1 = float(cfg["theta_max"])
    v0 = float(cfg["v_min"])
    v1 = float(cfg["v_max"])
    direction = str(cfg.get("direction", "CW")).upper()

    # 展開（CWでt1<t0など）に対応
    if direction == "CW" and t1 < t0:
        t1 += 360.0
    if direction == "CCW" and t1 < t0:
        t1 += 360.0

    a = ang
    if a < t0:
        a += 360.0
    a = max(min(a, t1), t0)

    # 線形変換
    return v0 + (a - t0) / (t1 - t0) * (v1 - v0)

def load_yaml(p): 
    with open(p, "r") as f:
        return yaml.safe_load(f)

def load_test_values(csv_path):
    m = {}
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            m[row["filename"]] = float(row["value_gt"])
    return m

def pick_best_det(result, conf_thres):
    if result.keypoints is None or len(result.keypoints) == 0:
        return None
    kpts = result.keypoints
    xyn = getattr(kpts, "xyn", None)
    xy = getattr(kpts, "xy", None)
    conf = getattr(kpts, "confidence", None) or getattr(kpts, "conf", None)
    boxes_conf = getattr(result.boxes, "conf", None) if result.boxes is not None else None

    best_idx, best_score = None, -1.0
    n = len(kpts)
    for i in range(n):
        kp_score = 0.0
        if conf is not None:
            try:
                c0 = float(conf[i][0].item()); c1 = float(conf[i][1].item())
                kp_score = (c0 + c1)/2.0
            except Exception:
                kp_score = 0.0
        box_score = 0.0
        if boxes_conf is not None and i < len(boxes_conf):
            try:
                box_score = float(boxes_conf[i].item())
            except Exception:
                box_score = 0.0
        score = 0.7*kp_score + 0.3*box_score
        if score > best_score:
            best_score, best_idx = score, i

    c0 = c1 = 1.0
    valid = True
    if conf is not None:
        try:
            c0 = float(conf[best_idx][0].item()); c1 = float(conf[best_idx][1].item())
        except Exception:
            pass
    if (c0 < conf_thres) or (c1 < conf_thres):
        valid = False

    return {"idx": best_idx, "valid": valid, "xyn": xyn, "xy": xy, "use_xyn": xyn is not None}

def to_pixels(best, img_w, img_h):
    i = best["idx"]
    if best["use_xyn"]:
        pv = best["xyn"][i][0].tolist()
        tp = best["xyn"][i][1].tolist()
        return (pv[0]*img_w, pv[1]*img_h), (tp[0]*img_w, tp[1]*img_h)
    else:
        pv = best["xy"][i][0].tolist()
        tp = best["xy"][i][1].tolist()
        return (pv[0], pv[1]), (tp[0], tp[1])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--test-images", required=True)
    ap.add_argument("--gauge-config", required=True)
    ap.add_argument("--test-values", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--conf-threshold", type=float, default=0.5)
    ap.add_argument("--viz", action="store_true")
    args = ap.parse_args()

    cfg = load_yaml(args.gauge_config)
    gt_values = load_test_values(args.test_values)

    out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    viz_dir = out_dir / "viz"; 
    if args.viz: viz_dir.mkdir(parents=True, exist_ok=True)

    model = YOLO(args.weights)
    img_paths = sorted(glob.glob(str(Path(args.test_images) / "*.*")))
    preds = model.predict(img_paths, imgsz=args.imgsz, conf=args.conf_threshold, verbose=False)

    rows = []
    errors = []
    for img_path, r in zip(img_paths, preds):
        name = Path(img_path).name
        if name not in gt_values:
            continue
        value_gt = gt_values[name]
        img = cv2.imread(img_path); h, w = img.shape[:2]

        best = pick_best_det(r, args.conf_threshold)
        angle_pred = None; value_pred = None; valid = False
        if best is not None:
            pv, tp = to_pixels(best, w, h)
            angle_pred = angle_deg(pv, tp)
            value_pred = map_angle_to_value(angle_pred, cfg)
            valid = best["valid"]

        value_err = None
        if value_pred is not None:
            value_err = abs(value_pred - value_gt)
            if valid:
                errors.append(value_err)

        rows.append({
            "filename": name,
            "value_gt": value_gt,
            "value_pred": value_pred if value_pred is not None else "",
            "value_err": value_err if value_err is not None else "",
            "angle_pred": angle_pred if angle_pred is not None else "",
            "valid": int(valid),
        })

        if args.viz and angle_pred is not None:
            pv, tp = to_pixels(best, w, h)
            canvas = img.copy()
            cv2.arrowedLine(canvas, (int(pv[0]), int(pv[1])), (int(tp[0]), int(tp[1])), (255,0,255), 2, tipLength=0.15)
            cv2.imwrite(str(viz_dir / f"{Path(img_path).stem}.jpg"), canvas)

    # CSV
    csv_path = Path(out_dir) / "value_results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)

    summary = {
        "mae_value": sum(errors)/len(errors) if errors else None,
        "num_samples_with_gt": len(rows),
        "num_valid": len(errors),
        "valid_ratio": (len(errors)/len(rows)) if rows else 0.0,
        "imgsz": args.imgsz,
        "conf_threshold": args.conf_threshold
    }
    with open(Path(out_dir) / "value_summary.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()