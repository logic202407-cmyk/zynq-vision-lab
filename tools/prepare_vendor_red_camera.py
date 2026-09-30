"""Prepare a private vendor camera build with original red statistics RTL.

The vendor HDL/XCI/XDC must already be available locally. This tool copies
them into an ASCII-only temporary build directory and makes narrow changes to
the packet header. No third-party source or bitstream is stored in this repo.
"""
import argparse
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source", type=Path, required=True,
                    help="local 30 FPS vendor trial root with rtl/, ip/, XDC and Tcl")
parser.add_argument("--output", type=Path, required=True,
                    help="new ASCII-only directory outside this repository")
parser.add_argument("--spatial-filter", action="store_true",
                    help="enable 3x3 majority and identify results as mask version 2")
args = parser.parse_args()
base = args.source.resolve()
dest = args.output.resolve()
repo = Path(__file__).resolve().parents[1]
if not dest.as_posix().isascii():
    parser.error("--output must be an ASCII-only path")
if dest == repo or repo in dest.parents:
    parser.error("--output must be outside the public repository")
if dest.exists():
    raise SystemExit(f"destination already exists: {dest}")
dest.mkdir(parents=True)
shutil.copytree(base / "rtl", dest / "rtl")
shutil.copytree(base / "ip", dest / "ip")
shutil.copyfile(base / "ov5640_udp_pc.xdc", dest / "ov5640_udp_pc.xdc")
for name in ("red_pixel_mask.v", "camera_rgb565_stream.v", "red_frame_stats.v",
             "red_result_header.v", "red_mask_majority3x3.v"):
    shutil.copyfile(repo / "src" / "rtl" / name, dest / "rtl" / name)


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match, got {count}: {old!r}")
    return text.replace(old, new)


top_path = dest / "rtl" / "ov5640_udp_pc.v"
top = top_path.read_text(encoding="latin1")
block = """
wire pl_pixel_valid, pl_frame_start, pl_frame_end;
wire [15:0] pl_pixel_rgb565;
wire [9:0] pl_pixel_x;
wire [8:0] pl_pixel_y;
wire pl_result_strobe, pl_frame_complete, pl_target_valid;
wire [18:0] pl_red_count;
wire [27:0] pl_red_sum_x, pl_red_sum_y;
wire [9:0] pl_red_min_x, pl_red_max_x;
wire [8:0] pl_red_min_y, pl_red_max_y;
wire [5:0] pl_header_index;
wire [7:0] pl_header_byte;

camera_rgb565_stream u_pl_camera_stream (
    .cam_pclk(cam_pclk), .rst_n(rst_n), .cam_vsync(cam_vsync),
    .cam_href(cam_href), .cam_data(cam_data),
    .pixel_valid(pl_pixel_valid), .frame_start(pl_frame_start),
    .frame_end(pl_frame_end), .pixel_rgb565(pl_pixel_rgb565),
    .pixel_x(pl_pixel_x), .pixel_y(pl_pixel_y)
);
red_frame_stats u_pl_red_stats (
    .clk(cam_pclk), .rst_n(rst_n), .pixel_valid(pl_pixel_valid),
    .frame_start(pl_frame_start), .frame_end(pl_frame_end),
    .pixel_rgb565(pl_pixel_rgb565), .pixel_x(pl_pixel_x), .pixel_y(pl_pixel_y),
    .result_strobe(pl_result_strobe), .frame_complete(pl_frame_complete),
    .target_valid(pl_target_valid), .red_count(pl_red_count),
    .red_sum_x(pl_red_sum_x), .red_sum_y(pl_red_sum_y),
    .red_min_x(pl_red_min_x), .red_min_y(pl_red_min_y),
    .red_max_x(pl_red_max_x), .red_max_y(pl_red_max_y)
);
red_result_header u_pl_red_header (
    .clk(cam_pclk), .rst_n(rst_n), .result_strobe(pl_result_strobe),
    .frame_complete(pl_frame_complete), .target_valid(pl_target_valid),
    .red_count(pl_red_count), .red_sum_x(pl_red_sum_x),
    .red_sum_y(pl_red_sum_y), .red_min_x(pl_red_min_x),
    .red_min_y(pl_red_min_y), .red_max_x(pl_red_max_x),
    .red_max_y(pl_red_max_y), .header_index(pl_header_index),
    .header_byte(pl_header_byte)
);

"""
if args.spatial_filter:
    block = block.replace("red_frame_stats u_pl_red_stats",
                          "red_frame_stats #(.SPATIAL_FILTER(1)) u_pl_red_stats")
    block = block.replace("red_result_header u_pl_red_header",
                          "red_result_header #(.MASK_VERSION(8'd2)) u_pl_red_header")
top = replace_once(top, "img_data_pkt u_img_data_pkt(", block + "img_data_pkt u_img_data_pkt(")
top = replace_once(top, ".rst_n              (rst_n),              \n   \n    .cam_pclk",
                   ".rst_n              (rst_n),              \n    .red_header_index   (pl_header_index),\n    .red_header_byte    (pl_header_byte),\n   \n    .cam_pclk")
top_path.write_text(top, encoding="latin1")

pkt_path = dest / "rtl" / "img_data_pkt.v"
pkt = pkt_path.read_text(encoding="latin1")
pkt = replace_once(pkt, "input                 rst_n          ,",
                   "input                 rst_n          ,\n    output       [5:0]     red_header_index,\n    input        [7:0]     red_header_byte,")
pkt = replace_once(pkt, "reg\t   [3 :0]\thead_cnt", "reg\t   [5 :0]\thead_cnt")
pkt = replace_once(pkt, "assign neg_vsync =", "assign red_header_index = head_cnt;\nassign neg_vsync =")
if pkt.count("head_cnt <= 4'd0") != 2:
    raise RuntimeError("unexpected vendor frame-header counter")
pkt = pkt.replace("head_cnt <= 4'd0", "head_cnt <= 6'd0")
pkt = replace_once(pkt, "head_cnt == 4'd8", "head_cnt == 6'd40")
pkt = replace_once(pkt, "head_cnt + 4'd1", "head_cnt + 6'd1")
pkt = replace_once(pkt, "head_cnt == 4'd7)\n\t\thead_flag", "head_cnt == 6'd39)\n\t\thead_flag")
pkt = replace_once(pkt, "\t\t\telse ;\t\n        end",
                   "\t\t\telse if(head_cnt < 6'd40)\n                wr_fifo_data <= red_header_byte;\n            else ;\t\n        end")
pkt = replace_once(pkt, "{CMOS_H_PIXEL,1'b0} + 16'd8", "{CMOS_H_PIXEL,1'b0} + 16'd40")
pkt_path.write_text(pkt, encoding="latin1")

preflight = (base / "preflight.tcl").read_text(encoding="utf-8")
preflight = preflight.replace("build3", "build")
(dest / "preflight.tcl").write_text(preflight, encoding="utf-8")
build = (base / "build_horizontal.tcl").read_text(encoding="utf-8").replace("build3", "build")
(dest / "build_red_trial.tcl").write_text(build, encoding="utf-8")
print(f"prepared {dest}")
