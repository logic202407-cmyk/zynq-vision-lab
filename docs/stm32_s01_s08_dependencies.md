# S02：SPL/CMSIS 本地原包来源与许可边界

固定manifest来自PR7 `04ba0db3e1a4f67cee7efa7b941d69ce281bffa2`，未修改。
本机找到 `STM32F10x_StdPeriph_Lib_V3.5.0.zip`，共1171成员；
包SHA-256为 `0e56bf5eb468d389355f86d4f2715acbb7c3f07e2bd86427caec4f5798846c2a`。
实际使用副本、ZIP成员和manifest的16文件hash全部相同。
这是本地包的字节来源证明，没有官方原始下载记录或官方公布hash证明此包真实性。
[ST当前产品页](https://www.st.com/en/embedded-software/stsw-stm32054.html) 只用于定位产品。

## 逐文件与许可材料

只读审计工具读取ZIP成员，记录每个文件的完整路径、实际SHA-256与版本头信息；
没有解压执行任何包成员，没有安装工具，没有改manifest。
16行完整结果将在本批报告的audit.json中保存，包含来源到CMSIS/CoreSupport、
DeviceSupport/ST/STM32F10x与StdPeriph_Driver的映射。

- CMSIS：包内 `Libraries/CMSIS/License.doc` 为39936字节Word97文档。
  通过Microsoft MS-DOC的CFB/WordDocument/piece table读取完整7307字符主文本，
  起始许可标题与末尾合约号 `LEC-PRE-00425-V2.0 NM/HB` 已逐段阅读核对。
  原文件hash `c0cf8934f8b63e5e021a3786d24f5b36280249774b06be300f8463b54e5beb99`，
  完整提取文本hash `b290f35fb61c0bf8ef89ec1dd8c866b47f254113db36732937647d5205fcaad0`。
  ARM条款约束CMSIS来源与使用范围，不能用来授权所有ST SPL文件。
- ST：根目录、DeviceSupport和StdPeriph_Driver的Release_Notes均有License小节。
  实际小节说明所附固件/相关文档没有License Agreement，如需该协议可联系ST办公室；
  后接参考用途和责任免责声明。根版本历史还记录V2.0.1移除了Firmware License文件。
  已保存三份材料hash与私有完整文本；不能从不存在协议文件推导MIT授权或公开转载许可。
- 没有取得独立ST许可协议或用户取得该包的官方下载凭据；没有替用户接受条款、联系ST、
  下载/安装新工具或上传厂商源、ZIP、License.doc及私有绝对目录。

因此S02已补齐本地原包16文件逐字节溯源和许可材料核对；
“完整授权证明”仍为 `blocked`，不能把S02整包宣称通过。
本批host只编译仓库自编portable C和测试bridge，不编译SPL/CMSIS支持源；
该缺口不阻止S04–S08。ARM固件重建与依赖公开复制未在本批执行。

文档读取方法参照[Microsoft MS-DOC文本定位](https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-doc/01d5d8c4-cf9c-4ef9-80fd-439e763cfe01)。
此处只记录实际材料和证据范围，不作法律效力或官方真实性保证。
