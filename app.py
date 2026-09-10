
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="VMware Assessment Visualizer",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root { --accent:#00a6a6; --panel:#101822; --muted:#8ea0b4; }
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 10% 0%, #102633 0, #0b1118 38%, #080d12 100%);
}
[data-testid="stSidebar"] { background:#0c141d; }
.block-container { padding-top:1.2rem; padding-bottom:2rem; max-width:1500px; }
h1,h2,h3 { letter-spacing:-0.02em; }
div[data-testid="stMetric"] {
    background:linear-gradient(145deg, rgba(22,35,48,.96), rgba(12,20,29,.96));
    border:1px solid rgba(140,170,190,.14);
    padding:18px 18px 14px;
    border-radius:18px;
}
div[data-testid="stMetricValue"] { font-size:1.75rem; }
.card {
    background:linear-gradient(145deg, rgba(18,29,40,.96), rgba(12,20,29,.96));
    border:1px solid rgba(140,170,190,.14);
    padding:16px 18px;
    border-radius:18px;
}
.small { color:#8ea0b4; font-size:.88rem; }
.badge { display:inline-block; padding:4px 9px; border-radius:999px; background:#173345; margin-right:6px; font-size:.78rem; }
</style>
""", unsafe_allow_html=True)

ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "assessment_data"

ENV_MAP = {
    "Production_10.80.18.122": "Production",
    "Flooz_10.80.18.112": "Flooz",
    "DMZ_10.82.11.120": "DMZ",
    "Site-Secors-Kpeme_10.80.24.122": "DR / Kpeme",
}

def find_assessment_root():
    candidates = [p for p in DATA_ROOT.rglob("*") if p.is_dir() and any((p / name).exists() for name in ["04-VMs.csv","03-ESXi-Hosts.csv"])]
    # Parent containing environment directories
    for p in DATA_ROOT.rglob("*"):
        if p.is_dir():
            children = [c.name for c in p.iterdir() if c.is_dir()] if p.exists() else []
            if sum(1 for c in children if c in ENV_MAP) >= 2:
                return p
    return DATA_ROOT

ASSESS_ROOT = find_assessment_root()

@st.cache_data(show_spinner=False)
def load_csv_group(filename):
    frames = []
    for folder, label in ENV_MAP.items():
        p = ASSESS_ROOT / folder / filename
        if p.exists():
            try:
                df = pd.read_csv(p, low_memory=False)
            except Exception:
                df = pd.read_csv(p, sep=";", low_memory=False)
            df["Environment"] = label
            df["SourceFolder"] = folder
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def num(df, col):
    if col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col].astype(str).str.replace(",", ".", regex=False), errors="coerce")

hosts = load_csv_group("03-ESXi-Hosts.csv")
vms = load_csv_group("04-VMs.csv")
disks = load_csv_group("05-VM-Disks.csv")
snaps = load_csv_group("06-Snapshots.csv")
datastores = load_csv_group("07-Datastores.csv")
stdpg = load_csv_group("08-Standard-PortGroups.csv")
vds = load_csv_group("09-Distributed-Switches.csv")
dvpg = load_csv_group("10-Distributed-PortGroups.csv")
vmk = load_csv_group("11-VMkernel-Network.csv")
pnics = load_csv_group("12-Physical-NICs.csv")
hbas = load_csv_group("13-HBAs.csv")
luns = load_csv_group("14-SCSI-LUNs.csv")
licenses = load_csv_group("15-Licenses.csv")
perf = load_csv_group("16-Performance-Summary.csv")
sizing = load_csv_group("18-Sizing-Input.csv")
vcenters = load_csv_group("00-vCenter.csv")

# Normalize common numeric fields
for df, cols in [
    (hosts, ["CpuCores","MemoryTotalGB"]),
    (datastores, ["CapacityGB","FreeSpaceGB","UsedSpaceGB","UsedPercent","VMCount"]),
    (sizing, ["HostCount","PoweredOnVMs","TotalPhysicalCores","TotalPhysicalMemoryGB","ProvisionedvCPU",
              "ProvisionedVMRAMGB","ProvisionedVMStorageGB","SumHostCpuMHz_P95","SumHostMemConsumedKB_P95"]),
]:
    for c in cols:
        if c in df.columns:
            df[c] = num(df, c)

if not sizing.empty:
    sizing["CPU_P95_GHz"] = sizing.get("SumHostCpuMHz_P95", 0) / 1000
    sizing["Mem_P95_TiB"] = sizing.get("SumHostMemConsumedKB_P95", 0) / 1024 / 1024 / 1024
    sizing["Storage_Prov_TiB"] = sizing.get("ProvisionedVMStorageGB", 0) / 1024
if not datastores.empty:
    if "UsedSpaceGB" not in datastores.columns and {"CapacityGB","FreeSpaceGB"}.issubset(datastores.columns):
        datastores["UsedSpaceGB"] = datastores["CapacityGB"] - datastores["FreeSpaceGB"]
    datastores["CapacityTiB"] = datastores.get("CapacityGB", 0)/1024
    datastores["UsedTiB"] = datastores.get("UsedSpaceGB", 0)/1024

# Sidebar
st.sidebar.markdown("## VMware Assessment")
st.sidebar.caption("Local interactive explorer")
all_envs = ["Tous"] + list(ENV_MAP.values())
env_sel = st.sidebar.multiselect("Environnements", list(ENV_MAP.values()), default=list(ENV_MAP.values()))
if not env_sel:
    env_sel = list(ENV_MAP.values())
search = st.sidebar.text_input("Recherche", placeholder="VM, hôte, datastore…")
st.sidebar.divider()
st.sidebar.caption(f"Données chargées depuis : `{ASSESS_ROOT.name}`")
st.sidebar.caption("Aucune connexion Internet n'est nécessaire pour les données.")

def filt(df):
    if df.empty: return df
    out = df[df["Environment"].isin(env_sel)].copy()
    return out

fh, fv, fs, fd = map(filt, [hosts, vms, snaps, datastores])
fsi, fp, fl, fpn, fhba = map(filt, [sizing, perf, luns, pnics, hbas])

if search:
    q=search.lower()
    def qf(df):
        if df.empty: return df
        mask = df.astype(str).apply(lambda col: col.str.lower().str.contains(q, na=False)).any(axis=1)
        return df[mask]
    # search only applies to detailed tables, not headline KPIs
else:
    qf=lambda x:x

# Header
st.markdown("# VMware Assessment Visualizer")
st.markdown(
    '<span class="badge">Production</span><span class="badge">Flooz</span><span class="badge">DMZ</span><span class="badge">DR / Kpeme</span>',
    unsafe_allow_html=True
)
st.caption("Exploration technique interactive de l'assessment VMware — inventaire, capacité, performances, stockage, snapshots, réseau et SAN.")

tabs = st.tabs(["Vue globale","Clusters & Performance","Hôtes","VMs","Stockage","Snapshots","Réseau & SAN","Données brutes"])

with tabs[0]:
    c1,c2,c3,c4,c5 = st.columns(5)
    total_hosts = len(fh)
    total_vms = len(fv)
    powered_on = int((fv.get("PowerState", pd.Series(dtype=str)).astype(str).str.lower()=="poweredon").sum()) if not fv.empty else 0
    cores = int(fh.get("CpuCores", pd.Series(dtype=float)).sum()) if not fh.empty else 0
    ram_tib = fh.get("MemoryTotalGB", pd.Series(dtype=float)).sum()/1024 if not fh.empty else 0
    c1.metric("Hôtes physiques", f"{total_hosts}")
    c2.metric("VM inventoriées", f"{total_vms}", f"{powered_on} sous tension")
    c3.metric("Cœurs CPU", f"{cores:,}".replace(","," "))
    c4.metric("RAM physique", f"{ram_tib:.2f} TiB")
    c5.metric("Snapshots", f"{len(fs)}")

    left,right = st.columns([1.15,1])
    with left:
        if not fv.empty:
            by_env = fv.groupby(["Environment","PowerState"]).size().reset_index(name="VMs")
            fig = px.bar(by_env, x="Environment", y="VMs", color="PowerState", barmode="stack",
                         title="Machines virtuelles par environnement et état")
            fig.update_layout(height=390, legend_title_text="", margin=dict(l=15,r=15,t=55,b=15))
            st.plotly_chart(fig, use_container_width=True)
    with right:
        if not fh.empty and "Model" in fh:
            m=fh.groupby("Model").size().reset_index(name="Hosts").sort_values("Hosts")
            fig=px.bar(m,x="Hosts",y="Model",orientation="h",title="Répartition des plateformes serveurs")
            fig.update_layout(height=390, margin=dict(l=15,r=15,t=55,b=15), yaxis_title="")
            st.plotly_chart(fig,use_container_width=True)

    if not fsi.empty:
        st.subheader("Demande P95 consolidée")
        a,b,c,d = st.columns(4)
        a.metric("CPU P95", f"{fsi['CPU_P95_GHz'].sum():.1f} GHz")
        b.metric("RAM P95", f"{fsi['Mem_P95_TiB'].sum():.2f} TiB")
        c.metric("vCPU provisionnés", f"{int(fsi.get('ProvisionedvCPU',pd.Series(dtype=float)).sum()):,}".replace(","," "))
        d.metric("Stockage VM provisionné", f"{fsi['Storage_Prov_TiB'].sum():.1f} TiB")

    if not fd.empty:
        hot90 = fd[fd.get("UsedPercent", pd.Series(dtype=float)) >= 90]
        inaccessible = fd[fd.get("Accessible", pd.Series(dtype=str)).astype(str).str.lower()=="false"] if "Accessible" in fd else pd.DataFrame()
        st.markdown(f"""
        <div class="card"><b>Points d'attention détectés</b><br>
        <span class="small">{len(hot90)} présentations de datastore sont à ≥ 90 % d'utilisation dans le périmètre sélectionné.
        {len(inaccessible)} présentation(s) sont marquées inaccessibles. Les valeurs de capacité peuvent inclure des présentations partagées et ne doivent pas être additionnées aveuglément pour un sizing final.</span></div>
        """, unsafe_allow_html=True)

with tabs[1]:
    if fsi.empty:
        st.info("Aucune donnée de sizing disponible.")
    else:
        st.subheader("Clusters et charge P95")
        c1,c2=st.columns(2)
        with c1:
            plot=fsi.sort_values("Mem_P95_TiB")
            fig=px.bar(plot,x="Mem_P95_TiB",y="Cluster",color="Environment",orientation="h",
                       title="Mémoire consommée P95 par cluster")
            fig.update_layout(height=470, xaxis_title="TiB", yaxis_title="", margin=dict(l=15,r=15,t=55,b=15))
            st.plotly_chart(fig,use_container_width=True)
        with c2:
            plot=fsi.sort_values("CPU_P95_GHz")
            fig=px.bar(plot,x="CPU_P95_GHz",y="Cluster",color="Environment",orientation="h",
                       title="CPU P95 par cluster")
            fig.update_layout(height=470, xaxis_title="GHz", yaxis_title="", margin=dict(l=15,r=15,t=55,b=15))
            st.plotly_chart(fig,use_container_width=True)

        cols=[c for c in ["Environment","Cluster","HostCount","PoweredOnVMs","TotalPhysicalCores","TotalPhysicalMemoryGB",
                           "ProvisionedvCPU","ProvisionedVMRAMGB","CPU_P95_GHz","Mem_P95_TiB","Storage_Prov_TiB"] if c in fsi.columns]
        st.dataframe(fsi[cols], use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("Inventaire ESXi")
    x=qf(fh)
    if not x.empty and "Model" in x:
        cols=[c for c in ["Environment","Host","Cluster","Model","ProcessorType","CpuSockets","CpuCores","MemoryTotalGB",
                           "ESXiVersion","Build","ConnectionState","PowerState","IsStandalone"] if c in x.columns]
        st.dataframe(x[cols],use_container_width=True,hide_index=True,height=540)
    else:
        st.info("Aucun hôte ne correspond au filtre.")

with tabs[3]:
    st.subheader("Inventaire des machines virtuelles")
    x=qf(fv)
    if not x.empty:
        cols=[c for c in ["Environment","Name","PowerState","Host","Cluster","NumCpu","MemoryGB","GuestOS","VMwareToolsStatus",
                           "HardwareVersion","ProvisionedSpaceGB","UsedSpaceGB","Datastore","Folder"] if c in x.columns]
        st.dataframe(x[cols],use_container_width=True,hide_index=True,height=600)
    else:
        st.info("Aucune VM ne correspond au filtre.")

with tabs[4]:
    st.subheader("Datastores")
    if not fd.empty:
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Présentations",len(fd))
        c2.metric("≥ 90 %",int((fd.get("UsedPercent",0)>=90).sum()))
        c3.metric("≥ 95 %",int((fd.get("UsedPercent",0)>=95).sum()))
        c4.metric("Capacité brute affichée",f"{fd['CapacityTiB'].sum():.1f} TiB")
        st.caption("La capacité brute affichée peut compter plusieurs fois un même stockage partagé. Utilisez les identifiants de LUN/WWN pour la déduplication finale.")

        top=fd.sort_values("UsedPercent",ascending=False).head(30)
        fig=px.bar(top.sort_values("UsedPercent"),x="UsedPercent",y="Datastore",color="Environment",orientation="h",
                   title="Top 30 des datastores les plus utilisés")
        fig.add_vline(x=90,line_dash="dash")
        fig.update_layout(height=650,xaxis_title="Utilisation (%)",yaxis_title="",margin=dict(l=15,r=15,t=55,b=15))
        st.plotly_chart(fig,use_container_width=True)

        x=qf(fd)
        cols=[c for c in ["Environment","Datastore","Type","CapacityGB","FreeSpaceGB","UsedSpaceGB","UsedPercent","VMCount","Accessible"] if c in x.columns]
        st.dataframe(x[cols].sort_values("UsedPercent",ascending=False),use_container_width=True,hide_index=True,height=550)
    else:
        st.info("Pas de données datastore.")

with tabs[5]:
    st.subheader("Snapshots")
    if not fs.empty:
        # derive age if possible
        created_col = next((c for c in ["Created","CreateTime","CreatedAt"] if c in fs.columns), None)
        if created_col:
            dt=pd.to_datetime(fs[created_col],errors="coerce",dayfirst=True)
            fs2=fs.copy()
            fs2["AgeDays"]=(pd.Timestamp.now().normalize()-dt).dt.days
            byenv=fs2.groupby("Environment").size().reset_index(name="Snapshots")
            fig=px.pie(byenv,names="Environment",values="Snapshots",hole=.55,title="Répartition des snapshots")
            fig.update_layout(height=390,margin=dict(l=15,r=15,t=55,b=15))
            st.plotly_chart(fig,use_container_width=True)
            cols=[c for c in ["Environment","VM","Name",created_col,"AgeDays","SizeGB","Description"] if c in fs2.columns]
            st.dataframe(qf(fs2)[cols].sort_values("AgeDays",ascending=False),use_container_width=True,hide_index=True,height=580)
        else:
            st.dataframe(qf(fs),use_container_width=True,hide_index=True,height=580)
    else:
        st.info("Aucun snapshot dans le périmètre.")

with tabs[6]:
    st.subheader("Réseau et SAN")
    a,b,c,d,e=st.columns(5)
    a.metric("vSwitch distribués",len(filt(vds)))
    b.metric("DV Port Groups",len(filt(dvpg)))
    c.metric("VMkernel",len(filt(vmk)))
    d.metric("pNIC",len(fpn))
    e.metric("HBA",len(fhba))
    subtabs=st.tabs(["vDS","DV Port Groups","VMkernel","pNIC","HBA","SCSI LUN"])
    for tab,df in zip(subtabs,[filt(vds),filt(dvpg),filt(vmk),fpn,fhba,fl]):
        with tab:
            st.dataframe(qf(df),use_container_width=True,hide_index=True,height=520)

with tabs[7]:
    st.subheader("Explorateur de données brutes")
    datasets={
        "vCenter":vcenters,"ESXi Hosts":hosts,"VMs":vms,"VM Disks":disks,"Snapshots":snaps,"Datastores":datastores,
        "Standard Port Groups":stdpg,"Distributed Switches":vds,"Distributed Port Groups":dvpg,"VMkernel":vmk,
        "Physical NICs":pnics,"HBAs":hbas,"SCSI LUNs":luns,"Licenses":licenses,"Performance":perf,"Sizing":sizing
    }
    choice=st.selectbox("Jeu de données",list(datasets))
    x=qf(filt(datasets[choice]))
    st.caption(f"{len(x):,} lignes × {len(x.columns)} colonnes".replace(","," "))
    st.dataframe(x,use_container_width=True,hide_index=True,height=650)
    st.download_button(
        "Exporter la vue CSV",
        data=x.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{choice.replace(' ','_')}_filtered.csv",
        mime="text/csv"
    )
