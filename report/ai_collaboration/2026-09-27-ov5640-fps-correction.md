# OV5640 frame-rate trial correction

- Initial hypothesis: reducing the vertical total from 984 to 862, using the vendor comment's 48 MHz pixel clock, would raise the 640×480 stream from about 26.3 to 30 FPS.
- Contradiction: the temporary vertical-trial bitstream passed Vivado bit generation and JTAG startup, but a 30 s receiver run assembled 0 complete frames while row-sized UDP datagrams kept arriving. A separate packet-length sample found no frame-start datagrams. Synthesis and timing reports did not predict this protocol failure.
- Controlled correction: a same-tool, same-upgraded-IP rebuild with the original 1856 × 984 timing produced 262 complete frames in 10 s. Keeping vertical total 984 and reducing horizontal total to 1626 produced 8999 complete frames in 300 s, with 0 incomplete frames. The failed vertical trial was restored to the known-good vendor bitstream before the control test.
- Communication correction: `490784008` received payload bytes over 30 s is about 16.36 MB/s, not 49 MB/s. The rate was recalculated from the raw counter.
- Boundary: the result supports this temporary board configuration only. The packet format cannot detect silent row errors, and a single inspected image plus a headless five-minute count do not establish complete image-quality or independent-reproduction acceptance.
