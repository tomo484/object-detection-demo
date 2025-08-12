import argparse, json, csv, math, os, glob
from pathlib import Path
import cv2
import yaml
from ultralytics import YOLO

def angle_deg(pivot_xy, tip_xy):
    dx = tip_xy[0] - pivot_xy[0]
    dy = tip_xy[1] - pivot_xy[1]
    ang = math.degrees(math.atan2(-dy,dx))
    return (ang + 360.0) % 360.0

def circ_abs_diff_deg(a, b):
    return abs(((a - b + 180.0) % 360.0) - 180.0)

def read_eval_cfg(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def load_image_size(img_path):
    img = cv2.imread(img_path)
    h, w = img.shape[: 2]
    return w, h, img

def read_gt_kpts(label_path, img_w, img_h):
    with open(label_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 11:
                x1 = float(parts[5]) * img_w
                y1 = float(parts[6]) * img_h
                v1 = int(float(parts[7]))
                x2 = float(parts[8]) * img_w
                y2 = float(parts[9]) * img_h
                v2 = int(float(parts[10]))
                return (x1, y1, v1), (x2, y2, v2)
    return None, None

def pick_best_det(result, conf_thres):
    if result.keypoints is None or len(result.keypoints) == 0:
        return None
    kpts = result.keypoints  # ultralytics.engine.results.Keypoints
    # xy normalized if available; prefer xyn then scale outside
    xyn = getattr(kpts, "xyn", None)
    xy = getattr(kpts, "xy", None)
    conf = getattr(kpts, "confidence", None) or getattr(kpts, "conf", None)
    # boxes conf fallback
    boxes_conf = getattr(result.boxes, "conf", None) if result.boxes is not None else None

    best_idx, best_score = None, -1.0
    n = len(kpts)
    for i in range(n):
        # use KP conf avg of first two points if present
        kp_score = 0.0
        if conf is not None:
            try:
                c0 = float(conf[i][0].item())
                c1 = float(conf[i][1].item())
                kp_score = (c0 + c1) / 2.0
            except Exception:
                kp_score = 0.0
        box_score = 0.0
        if boxes_conf is not None and i < len(boxes_conf):
            try:
                box_score = float(boxes_conf[i].item())
            except Exception:
                box_score = 0.0
        score = 0.7 * kp_score + 0.3 * box_score
        if score > best_score:
            best_score = score
            best_idx = i

    # confidence gate for validity
    valid = True
    c0 = c1 = 1.0
    if conf is not None:
        try:
            c0 = float(conf[best_idx][0].item())
            c1 = float(conf[best_idx][1].item())
        except Exception:
            pass
    if (c0 < conf_thres) or (c1 < conf_thres):
        valid = False

    # return structure with xy normalized or absolute
    return {
        "idx": best_idx,
        "valid": valid,
        "use_xyn": xyn is not None,
        "xyn": xyn,
        "xy": xy,
        "conf_pair": (c0, c1),
    }

def to_pixels_from_result(best, img_w, img_h):
    i = best["idx"]
    if best["use_xyn"]:
        tp = best["xyn"][i][0].tolist()  # [x, y]
        pv = best["xyn"][i][1].tolist()
        tip_xy = (tp[0] * img_w, tp[1] * img_h)
        pivot_xy = (pv[0] * img_w, pv[1] * img_h)
    else:
        tp = best["xy"][i][0].tolist()
        pv = best["xy"][i][1].tolist()
        pivot_xy = (pv[0], pv[1])
        tip_xy = (tp[0], tp[1])
    return pivot_xy, tip_xy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = read_eval_cfg(args.config)

    imgsz = int(cfg.get("imgsz", 640))
    conf_thres = float(cfg.get("conf_threshold", 0.5))
    weights = cfg["weights"]
    test_images = cfg["test_images"]
    test_labels = cfg["test_labels"]
    out_dir = Path(cfg["out_dir"])
    do_viz = bool(cfg.get("viz", True))
    out_dir.mkdir(parents=True, exist_ok=True)
    viz_dir = out_dir / "viz"
    if do_viz:
        viz_dir.mkdir(parents=True, exist_ok=True)

    model = YOLO(weights)
    img_paths = sorted(glob.glob(str(Path(test_images) / "*.*")))
    preds = model.predict(img_paths, imgsz=imgsz, conf=conf_thres, verbose=False)

    rows = []
    valid_errors = []
    for img_path, r in zip(img_paths, preds):
        stem = Path(img_path).stem
        label_path = Path(test_labels) / f"{stem}.txt"
        img_w, img_h, img = load_image_size(img_path)

        gt_pv, gt_tp = read_gt_kpts(str(label_path), img_w, img_h)
        angle_gt, gt_visible = None, True
        if gt_pv and gt_tp:
            angle_gt = angle_deg((gt_pv[0], gt_pv[1]), (gt_tp[0], gt_tp[1]))
            gt_visible = (gt_pv[2] > 0) and (gt_tp[2] > 0)

        best = pick_best_det(r, conf_thres)
        angle_pred, valid = None, False
        if best is not None:
            pv_xy, tp_xy = to_pixels_from_result(best, img_w, img_h)
            angle_pred = angle_deg(pv_xy, tp_xy)
            valid = best["valid"]

        err = None
        if (angle_gt is not None) and (angle_pred is not None):
            err = circ_abs_diff_deg(angle_pred, angle_gt)
            if valid:
                valid_errors.append(err)

        rows.append({
            "filename": Path(img_path).name,
            "angle_gt": angle_gt if angle_gt is not None else "",
            "angle_pred": angle_pred if angle_pred is not None else "",
            "angle_err_deg": err if err is not None else "",
            "valid": int(valid),
            "gt_visible": int(gt_visible),
        })

        if do_viz and (angle_gt is not None or angle_pred is not None):
            canvas = img.copy()
            if angle_gt is not None:
                cv2.arrowedLine(canvas, (int(gt_pv[0]), int(gt_pv[1])), (int(gt_tp[0]), int(gt_tp[1])), (0,255,0), 2, tipLength=0.15)
            if angle_pred is not None:
                cv2.arrowedLine(canvas, (int(pv_xy[0]), int(pv_xy[1])), (int(tp_xy[0]), int(tp_xy[1])), (255,0,255), 2, tipLength=0.15)
            cv2.imwrite(str(viz_dir / f"{stem}.jpg"), canvas)

    # CSV
    csv_path = out_dir / "angle_results.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    summary = {
        "mae_deg": sum(valid_errors)/len(valid_errors) if valid_errors else None,
        "num_samples": len(rows),
        "num_valid": len(valid_errors),
        "valid_ratio": (len(valid_errors)/len(rows)) if rows else 0.0,
        "conf_threshold": conf_thres,
        "imgsz": imgsz
    }
    with open(out_dir / "angle_summary.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()