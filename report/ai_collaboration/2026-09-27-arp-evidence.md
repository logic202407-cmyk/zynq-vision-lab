# ARP bring-up inference correction

- Initial observation: the vendor camera bitstream was configured, but the PC could not resolve `192.168.1.10` and received no UDP frames. Suspected board transmit failure was a hypothesis, not a verified diagnosis.
- Test: a temporary ARP-reply diagnostic reused local vendor ARP receive/transmit logic. The host received one ARP reply and learned MAC `00-11-22-33-44-55`; the user observed both diagnostic LEDs latched on. A ping timeout did not contradict this result because the diagnostic did not implement ICMP.
- Correction: the physical GE transmit path works in that diagnostic. Reloading the vendor camera bitstream while the host retained the learned MAC produced live UDP video and complete 640×480 frames. The remaining problem is repeatable standalone ARP startup for the vendor camera bitstream, whose exact cause is still unknown.
- Evidence boundary: a few 5–10 second live runs do not satisfy the planned five-minute baseline or power-cycle reproduction. Diagnostic source, vendor HDL and private camera images remain outside this public repository.
