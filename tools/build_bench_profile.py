import argparse,hashlib,json,re,shutil,struct,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description='Rebuild a preserved bench profile; never flashes or enables hardware.')
p.add_argument('--profile',required=True,choices=['legacy_reversal','legacy_continuous_pan','red_position','static_spot','red_static_steady','three_camera_rx','laser12_static','laser123_with_camera_rx','laser123_static'])
p.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1])
p.add_argument('--stage',type=Path,required=True)
p.add_argument('--toolchain',type=Path,default=Path('D:/Keil_ARM/ARM/ARMCLANG/bin'))
args=p.parse_args();args.team_profile=True
root=args.source_root
base=root/'src/prototype/skystar_openmv'
fw=base/'profiles'/args.profile
shared=fw/'shared' if (fw/'shared').is_dir() else base/'stm32_project/User'
stage=args.stage
stage.mkdir(parents=True,exist_ok=True)
tools=args.toolchain
sources=list((fw/'User').glob('*.[ch]'))+[shared/'pid.c',shared/'pid.h',fw/'startup.s',fw/'firmware.sct']
for p in sources:shutil.copyfile(p,stage/p.name)
compat='''/* ARMCC5 intrinsics expressed for Arm Compiler 6. No device access here. */
#define __schedule_barrier() __asm volatile ("" ::: "memory")
#define __disable_irq() __asm volatile ("cpsid i" ::: "memory")
#define __enable_irq() __asm volatile ("cpsie i" ::: "memory")
'''
(stage/'ac6_compat.h').write_text(compat)
commands=[]
def run(name,cmd):
 p=subprocess.run([str(x) for x in cmd],cwd=stage,capture_output=True)
 log=(p.stdout+p.stderr).decode(errors='replace')
 (stage/(name+'.log')).write_text(log)
 commands.append({'name':name,'command':list(map(str,cmd)),'exit_code':p.returncode})
 if p.returncode:raise RuntimeError(name+'\n'+log)
 return log
version=run('version',[tools/'armclang.exe','--version'])
flags=['--target=arm-arm-none-eabi','-mcpu=cortex-m4','-mfloat-abi=soft','-std=c99','-Oz','-ffunction-sections','-fdata-sections','-D__MICROLIB','-DCONSOLE_USART=3','-DS1ACK1','-DC1_OBSERVATIONS','-DC1_CLOSED_LOOP','-include','ac6_compat.h','-Wall','-Wextra','-Werror']
objects=[]
if args.team_profile:flags.append('-DSKYSTAR_TEAM_PROFILE')
for p in sorted(stage.glob('*.c')):
 obj=p.with_suffix('.o').name
 run(p.stem,[tools/'armclang.exe',*flags,'-c',p.name,'-o',obj]);objects.append(obj)
run('startup',[tools/'armasm.exe','--cpu=Cortex-M4','startup.s','-o','startup.o'])
run('link',[tools/'armlink.exe','--cpu=Cortex-M4','--library_type=microlib','--scatter=firmware.sct','--map','--info=sizes','--list=firmware.map','--output=skystar_tracking.axf','startup.o',*objects])
run('bin',[tools/'fromelf.exe','--bin','--output=skystar_tracking.bin','skystar_tracking.axf'])
run('hex',[tools/'fromelf.exe','--i32combined','--output=skystar_tracking.hex','skystar_tracking.axf'])
run('disassembly',[tools/'fromelf.exe','--text','-c','skystar_tracking.axf'])
b=(stage/'skystar_tracking.bin').read_bytes()
fmt=b'F1 %08lx%08lx %08lx %08lx %04x %04x %x'
assert len(b)>=8 # Marker strings differ across historical profiles; vectors and size are checked below.
assert len(b)<=16384
sp,reset=struct.unpack('<II',b[:8]);assert 0x20000000<sp<=0x20020000 and reset&1 and 0x08000000<=reset<0x08000000+len(b)
warnings={p.name:re.findall(r'^.*[Ww]arning.*$',p.read_text(),re.M) for p in stage.glob('*.log') if p.name!='disassembly.log'}
report={'scope':'Offline AC6 rebuild; historical hash comparison recorded below; not programmed','compiler':version,'console_usart':3,'s1ack1':True,'c1_observations':True,'c1_closed_loop':True,'binary_bytes':len(b),'f1_format_offset':b.find(fmt),'stack_pointer':hex(sp),'reset_vector':hex(reset),'source_sha256':{str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'compatibility_header_sha256':hashlib.sha256(compat.encode()).hexdigest(),'artifacts':{n:hashlib.sha256((stage/n).read_bytes()).hexdigest() for n in ['skystar_tracking.bin','skystar_tracking.axf','skystar_tracking.hex','firmware.map']},'commands':commands,'warnings':{k:v for k,v in warnings.items() if v}}
report['compatibility_header_sha256']=hashlib.sha256((stage/'ac6_compat.h').read_bytes()).hexdigest()
report['team_profile']=args.team_profile
report['profile']=args.profile
manifest=json.loads((root/'report/evidence/full-progress-20261104/manifest.json').read_text(encoding='utf-8'))
expected=(manifest['profiles'].get(args.profile) or {}).get('expected_binary_sha256')
report['expected_binary_sha256']=expected
report['matches_historical_binary']=None if not expected else report['artifacts']['skystar_tracking.bin']==expected
(stage/'build.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ['source_sha256','commands']},indent=2))
if report['matches_historical_binary'] is False:raise SystemExit('Rebuild differs from historical binary; inspect build report, no hardware actions taken.')
