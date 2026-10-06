from flask import Flask, render_template_string, request, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

app = Flask(__name__)

def get_fractal_resistance(df):
    if len(df) < 6: return None
    for i in range(len(df) - 4, 2, -1):
        if (df['High'].iloc[i] > df['High'].iloc[i-1] and 
            df['High'].iloc[i] > df['High'].iloc[i-2] and 
            df['High'].iloc[i] > df['High'].iloc[i+1] and 
            df['High'].iloc[i] > df['High'].iloc[i+2]):
            return df['High'].iloc[i]
    return None

def cek_breakout(simbol, df):
    try:
        df = df.dropna()
        if df.empty or len(df) < 6: return None
        
        resistance = get_fractal_resistance(df)
        if resistance is None: return None
        
        high_hari_ini = df['High'].iloc[-1]
        close_hari_ini = df['Close'].iloc[-1]
        close_kemarin = df['Close'].iloc[-2]
        volume_hari_ini = df['Volume'].iloc[-1]
        high_kemarin = df['High'].iloc[-2]

        change_pct = ((close_hari_ini - close_kemarin) / close_kemarin) * 100

        if high_hari_ini > resistance and high_kemarin <= resistance:
            if volume_hari_ini > 5000000:
                status = "CLOSE ABOVE" if close_hari_ini > resistance else "HIGH ONLY"
                return {
                    "simbol": simbol.replace('.JK', ''), 
                    "status": status, 
                    "price": float(close_hari_ini),
                    "change": float(change_pct),
                    "vol": int(volume_hari_ini), 
                    "res": float(resistance)
                }
        return None
    except Exception as e:
        return None

@app.route('/api/scan', methods=['POST'])
def scan_api():
    req_data = request.get_json()
    batch_saham = req_data.get('symbols', [])
    
    if not batch_saham:
        return jsonify([])

    data = yf.download(batch_saham, period="1mo", interval="1d", group_by='ticker', progress=False)
    
    results = []
    for s in batch_saham:
        try:
            df_saham = data[s] if len(batch_saham) > 1 else data
            res = cek_breakout(s, df_saham)
            if res: results.append(res)
        except Exception:
            continue
            
    return jsonify(results)

@app.route('/')
def home():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Stock Breakout Scanner</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
            body { font-family: 'Inter', sans-serif; background-color: #f3f4f6; }
            .indicator { transition: background-color 0.3s; }
            /* Tambahan efek untuk kolom yang bisa disortir */
            th { transition: background-color 0.2s; }
        </style>
    </head>
    <body class="p-4 md:p-10">
        <div class="max-w-5xl mx-auto">
            
            <!-- Tombol Aksi di Luar Area Capture -->
            <div class="flex justify-between items-end mb-4">
                <div></div> <!-- Placeholder -->
                <button id="btn-scan" class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-bold shadow transition-colors">
                    Mulai Scan
                </button>
            </div>

            <div id="capture-area" class="bg-white p-8 rounded-xl shadow-lg border border-gray-200">
                
                <!-- Header & Indicator -->
                <div class="flex justify-between items-start mb-6">
                    <div>
                        <h1 class="text-3xl font-bold text-gray-800 flex items-center gap-3">
                            🚀 Fractal Breakout Watchlist
                            <div id="status-indicator" class="w-4 h-4 rounded-full bg-red-500 indicator" title="Belum Selesai"></div>
                        </h1>
                        <p id="progress-text" class="text-gray-500 mt-1">Siap memulai scan. (0 / 963 Emiten)</p>
                    </div>
                    <div class="text-right">
                        <p class="text-sm font-semibold text-gray-400 uppercase tracking-wider">Waktu Selesai</p>
                        <p id="timestamp-text" class="text-lg font-mono text-blue-600">-</p>
                    </div>
                </div>

                <!-- Table Area -->
                <div class="overflow-hidden rounded-lg border border-gray-200">
                    <table class="w-full text-left border-collapse">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-4 text-sm font-semibold text-gray-700 uppercase cursor-pointer hover:bg-gray-200 select-none" onclick="sortTable(0, 'str')" title="Sort Ticker">Ticker ↕</th>
                                <th class="px-6 py-4 text-sm font-semibold text-gray-700 uppercase cursor-pointer hover:bg-gray-200 select-none" onclick="sortTable(1, 'str')" title="Sort Status">Status ↕</th>
                                <th class="px-6 py-4 text-sm font-semibold text-gray-700 uppercase text-right cursor-pointer hover:bg-gray-200 select-none" onclick="sortTable(2, 'num')" title="Sort Price">Price ↕</th>
                                <th class="px-6 py-4 text-sm font-semibold text-gray-700 uppercase text-right cursor-pointer hover:bg-gray-200 select-none" onclick="sortTable(3, 'num')" title="Sort Change">Change (%) ↕</th>
                                <th class="px-6 py-4 text-sm font-semibold text-gray-700 uppercase text-right cursor-pointer hover:bg-gray-200 select-none" onclick="sortTable(4, 'num')" title="Sort Up Fractal">Up Fractal ↕</th>
                                <th class="px-6 py-4 text-sm font-semibold text-gray-700 uppercase text-right cursor-pointer hover:bg-gray-200 select-none" onclick="sortTable(5, 'num')" title="Sort Volume">Volume ↕</th>
                            </tr>
                        </thead>
                        <tbody id="result-body" class="divide-y divide-gray-200">
                            <!-- Hasil akan di-inject ke sini oleh JavaScript -->
                        </tbody>
                    </table>
                </div>

                <!-- Footer Informasi -->
                <div class="mt-6 pt-6 border-t border-gray-100 text-xs text-gray-400 flex justify-between">
                    <span>Develop by MOSYA (https://stockbit.com/mohsyaifudin93)</span>
                    <span>Data provided by Yahoo Finance</span>
                </div>
            </div>

            <!-- Tombol Download -->
            <div class="mt-8 flex justify-center">
                <button onclick="downloadImage()" class="bg-emerald-600 hover:bg-emerald-700 text-white px-8 py-3 rounded-full font-bold shadow-lg transition-all transform hover:scale-105 flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
                    </svg>
                    Simpan Hasil (JPEG)
                </button>
            </div>
        </div>

        <script>
            // Daftar Emiten (Masukkan semua kode Anda di sini)
            const allSymbols = [
                'AADI.JK', 'AALI.JK', 'ABBA.JK', 'ABDA.JK', 'ABMM.JK', 'ACES.JK', 'ACRO.JK', 'ACST.JK', 'ADCP.JK', 'ADES.JK', 'ADHI.JK', 'ADMF.JK', 'ADMG.JK', 'ADMR.JK', 'ADRO.JK', 'AEGS.JK', 'AGAR.JK', 'AGII.JK', 'AGRO.JK', 'AGRS.JK', 'AHAP.JK', 'AIMS.JK', 'AISA.JK', 'AKKU.JK', 'AKPI.JK', 'AKRA.JK', 'AKSI.JK', 'ALDO.JK', 'ALII.JK', 'ALKA.JK', 'ALMI.JK', 'ALTO.JK', 'AMAG.JK', 'AMAN.JK', 'AMAR.JK', 'AMFG.JK', 'AMIN.JK', 'AMMN.JK', 'AMMS.JK', 'AMOR.JK', 'AMRT.JK', 'ANDI.JK', 'ANJT.JK', 'ANTM.JK', 'APEX.JK', 'APIC.JK', 'APII.JK', 'APLI.JK', 'APLN.JK', 'ARCI.JK', 'AREA.JK', 'ARGO.JK', 'ARII.JK', 'ARKA.JK', 'ARKO.JK', 'ARMY.JK', 'ARNA.JK', 'ARTA.JK', 'ARTI.JK', 'ARTO.JK', 'ASBI.JK', 'ASDM.JK', 'ASGR.JK', 'ASHA.JK', 'ASII.JK', 'ASJT.JK', 'ASLC.JK', 'ASLI.JK', 'ASMI.JK', 'ASPI.JK', 'ASPR.JK', 'ASRI.JK', 'ASRM.JK', 'ASSA.JK', 'ATAP.JK', 'ATIC.JK', 'ATLA.JK', 'AUTO.JK', 'AVIA.JK', 'AWAN.JK', 'AXIO.JK', 'AYAM.JK', 'AYLS.JK', 'BABP.JK', 'BABY.JK', 'BACA.JK', 'BACH.JK', 'BAIK.JK', 'BAJA.JK', 'BALI.JK', 'BANK.JK', 'BAPA.JK', 'BAPI.JK', 'BATA.JK', 'BATR.JK', 'BAUT.JK', 'BAYU.JK', 'BBCA.JK', 'BBHI.JK', 'BBKP.JK', 'BBLD.JK', 'BBMD.JK', 'BBNI.JK', 'BBRI.JK', 'BBRM.JK', 'BBSI.JK', 'BBSS.JK', 'BBTN.JK', 'BBYB.JK', 'BCAP.JK', 'BCIC.JK', 'BCIP.JK', 'BDKR.JK', 'BDMN.JK', 'BEBS.JK', 'BEEF.JK', 'BEER.JK', 'BEKS.JK', 'BELI.JK', 'BELL.JK', 'BESS.JK', 'BEST.JK', 'BFIN.JK', 'BGTG.JK', 'BHAT.JK', 'BHIT.JK', 'BIKA.JK', 'BIKE.JK', 'BIMA.JK', 'BINA.JK', 'BINO.JK', 'BIPI.JK', 'BIPP.JK', 'BIRD.JK', 'BISI.JK', 'BJBR.JK', 'BJTM.JK', 'BKDP.JK', 'BKSL.JK', 'BKSW.JK', 'BLES.JK', 'BLOG.JK', 'BLTA.JK', 'BLTZ.JK', 'BLUE.JK', 'BMAS.JK', 'BMBL.JK', 'BMHS.JK', 'BMRI.JK', 'BMSR.JK', 'BMTR.JK', 'BNBA.JK', 'BNBR.JK', 'BNGA.JK', 'BNII.JK', 'BNLI.JK', 'BOAT.JK', 'BOBA.JK', 'BOGA.JK', 'BOLA.JK', 'BOLT.JK', 'BOSS.JK', 'BPFI.JK', 'BPII.JK', 'BPTR.JK', 'BRAM.JK', 'BREN.JK', 'BRIS.JK', 'BRMS.JK', 'BRNA.JK', 'BRPT.JK', 'BRRC.JK', 'BSBK.JK', 'BSDE.JK', 'BSIM.JK', 'BSML.JK', 'BSSR.JK', 'BSWD.JK', 'BTEK.JK', 'BTEL.JK', 'BTON.JK', 'BTPN.JK', 'BTPS.JK', 'BUAH.JK', 'BUDI.JK', 'BUKA.JK', 'BUKK.JK', 'BULL.JK', 'BUMI.JK', 'BUVA.JK', 'BVIC.JK', 'BWPT.JK', 'BYAN.JK', 'CAKK.JK', 'CAMP.JK', 'CANI.JK', 'CARE.JK', 'CARS.JK', 'CASA.JK', 'CASH.JK', 'CASS.JK', 'CBDK.JK', 'CBMF.JK', 'CBPE.JK', 'CBRE.JK', 'CBUT.JK', 'CCSI.JK', 'CDIA.JK', 'CEKA.JK', 'CENT.JK', 'CFIN.JK', 'CGAS.JK', 'CHEK.JK', 'CHEM.JK', 'CHIP.JK', 'CINT.JK', 'CITA.JK', 'CITY.JK', 'CLAY.JK', 'CLEO.JK', 'CLPI.JK', 'CMNP.JK', 'CMNT.JK', 'CMPP.JK', 'CMRY.JK', 'CNKO.JK', 'CNMA.JK', 'CNTX.JK', 'COAL.JK', 'COCO.JK', 'COIN.JK', 'COWL.JK', 'CPIN.JK', 'CPRI.JK', 'CPRO.JK', 'CRAB.JK', 'CRSN.JK', 'CSAP.JK', 'CSIS.JK', 'CSMI.JK', 'CSRA.JK', 'CTBN.JK', 'CTRA.JK', 'CTTH.JK', 'CUAN.JK', 'CYBR.JK', 'DAAZ.JK', 'DADA.JK', 'DART.JK', 'DATA.JK', 'DAYA.JK', 'DCII.JK', 'DEAL.JK', 'DEFI.JK', 'DEPO.JK', 'DEWA.JK', 'DEWI.JK', 'DFAM.JK', 'DGIK.JK', 'DGNS.JK', 'DGWG.JK', 'DIGI.JK', 'DILD.JK', 'DIVA.JK', 'DKFT.JK', 'DKHH.JK', 'DLTA.JK', 'DMAS.JK', 'DMMX.JK', 'DMND.JK', 'DNAR.JK', 'DNET.JK', 'DOID.JK', 'DOOH.JK', 'DOSS.JK', 'DPNS.JK', 'DPUM.JK', 'DRMA.JK', 'DSFI.JK', 'DSNG.JK', 'DSSA.JK', 'DUCK.JK', 'DUTI.JK', 'DVLA.JK', 'DWGL.JK', 'DYAN.JK', 'EAST.JK', 'ECII.JK', 'EDGE.JK', 'EKAD.JK', 'ELIT.JK', 'ELPI.JK', 'ELSA.JK', 'ELTY.JK', 'EMAS.JK', 'EMDE.JK', 'EMMI.JK', 'EMTK.JK', 'ENAK.JK', 'ENRG.JK', 'ENVY.JK', 'ENZO.JK', 'EPAC.JK', 'EPMT.JK', 'ERAA.JK', 'ERAL.JK', 'ERTX.JK', 'ESIP.JK', 'ESSA.JK', 'ESTA.JK', 'ESTI.JK', 'ETWA.JK', 'EURO.JK', 'EXCL.JK', 'FAPA.JK', 'FAST.JK', 'FASW.JK', 'FILM.JK', 'FIMP.JK', 'FIRE.JK', 'FISH.JK', 'FITT.JK', 'FLMC.JK', 'FMII.JK', 'FOLK.JK', 'FOOD.JK', 'FORE.JK', 'FORU.JK', 'FPNI.JK', 'FUJI.JK', 'FUTR.JK', 'FWCT.JK', 'GAMA.JK', 'GDST.JK', 'GDYR.JK', 'GEMA.JK', 'GEMS.JK', 'GGRM.JK', 'GGRP.JK', 'GHON.JK', 'GIAA.JK', 'GJTL.JK', 'GLOB.JK', 'GLVA.JK', 'GMFI.JK', 'GMTD.JK', 'GOLD.JK', 'GOLF.JK', 'GOLL.JK', 'GOOD.JK', 'GOTO.JK', 'GPRA.JK', 'GPSO.JK', 'GRIA.JK', 'GRPH.JK', 'GRPM.JK', 'GSMF.JK', 'GTBO.JK', 'GTRA.JK', 'GTSI.JK', 'GULA.JK', 'GUNA.JK', 'GWSA.JK', 'GZCO.JK', 'HADE.JK', 'HAIS.JK', 'HAJJ.JK', 'HALO.JK', 'HATM.JK', 'HBAT.JK', 'HDFA.JK', 'HDIT.JK', 'HEAL.JK', 'HELI.JK', 'HERO.JK', 'HEXA.JK', 'HGII.JK', 'HILL.JK', 'HITS.JK', 'HKMU.JK', 'HMSP.JK', 'HOKI.JK', 'HOME.JK', 'HOMI.JK', 'HOPE.JK', 'HOTL.JK', 'HRME.JK', 'HRTA.JK', 'HRUM.JK', 'HUMI.JK', 'HYGN.JK', 'IATA.JK', 'IBFN.JK', 'IBOS.JK', 'IBST.JK', 'ICBP.JK', 'ICON.JK', 'IDEA.JK', 'IDPR.JK', 'IFII.JK', 'IFSH.JK', 'IGAR.JK', 'IIKP.JK', 'IKAI.JK', 'IKAN.JK', 'IKBI.JK', 'IKPM.JK', 'IMAS.JK', 'IMJS.JK', 'IMPC.JK', 'INAF.JK', 'INAI.JK', 'INCF.JK', 'INCI.JK', 'INCO.JK', 'INDF.JK', 'INDO.JK', 'INDR.JK', 'INDS.JK', 'INDX.JK', 'INDY.JK', 'INET.JK', 'INKP.JK', 'INOV.JK', 'INPC.JK', 'INPP.JK', 'INPS.JK', 'INRU.JK', 'INTA.JK', 'INTD.JK', 'INTP.JK', 'IOTF.JK', 'IPAC.JK', 'IPCC.JK', 'IPCM.JK', 'IPOL.JK', 'IPPE.JK', 'IPTV.JK', 'IRRA.JK', 'IRSX.JK', 'ISAP.JK', 'ISAT.JK', 'ISEA.JK', 'ISSP.JK', 'ITIC.JK', 'ITMA.JK', 'ITMG.JK', 'JARR.JK', 'JAST.JK', 'JATI.JK', 'JAWA.JK', 'JAYA.JK', 'JECC.JK', 'JECX.JK', 'JELI.JK', 'JGLE.JK', 'JIHD.JK', 'JKON.JK', 'JMAS.JK', 'JPFA.JK', 'JRPT.JK', 'JSKY.JK', 'JSMR.JK', 'JSPT.JK', 'JTPE.JK', 'KAEF.JK', 'KAQI.JK', 'KARW.JK', 'KAYU.JK', 'KBAG.JK', 'KBLI.JK', 'KBLM.JK', 'KBLV.JK', 'KBRI.JK', 'KDSI.JK', 'KDTN.JK', 'KEEN.JK', 'KEJU.JK', 'KETR.JK', 'KIAS.JK', 'KICI.JK', 'KIJA.JK', 'KING.JK', 'KINO.JK', 'KIOS.JK', 'KJEN.JK', 'KKES.JK', 'KKGI.JK', 'KLAS.JK', 'KLBF.JK', 'KLIN.JK', 'KMDS.JK', 'KMTR.JK', 'KOBX.JK', 'KOCI.JK', 'KOIN.JK', 'KOKA.JK', 'KONI.JK', 'KOPI.JK', 'KOTA.JK', 'KPIG.JK', 'KRAS.JK', 'KREN.JK', 'KRYA.JK', 'KSIX.JK', 'KUAS.JK', 'LABA.JK', 'LABS.JK', 'LAJU.JK', 'LAND.JK', 'LAPD.JK', 'LCGP.JK', 'LCKM.JK', 'LEAD.JK', 'LFLO.JK', 'LIFE.JK', 'LINK.JK', 'LION.JK', 'LIVE.JK', 'LMAS.JK', 'LMAX.JK', 'LMPI.JK', 'LMSH.JK', 'LOPI.JK', 'LPCK.JK', 'LPGI.JK', 'LPIN.JK', 'LPKR.JK', 'LPLI.JK', 'LPPF.JK', 'LPPS.JK', 'LRNA.JK', 'LSIP.JK', 'LTLS.JK', 'LUCK.JK', 'LUCY.JK', 'MABA.JK', 'MAGP.JK', 'MAHA.JK', 'MAIN.JK', 'MANG.JK', 'MAPA.JK', 'MAPB.JK', 'MAPI.JK', 'MARI.JK', 'MARK.JK', 'MASB.JK', 'MAXI.JK', 'MAYA.JK', 'MBAP.JK', 'MBMA.JK', 'MBSS.JK', 'MBTO.JK', 'MCAS.JK', 'MCOL.JK', 'MCOR.JK', 'MDIA.JK', 'MDIY.JK', 'MDKA.JK', 'MDKI.JK', 'MDLA.JK', 'MDLN.JK', 'MDRN.JK', 'MEDC.JK', 'MEDS.JK', 'MEGA.JK', 'MEJA.JK', 'MENN.JK', 'MERI.JK', 'MERK.JK', 'META.JK', 'MFMI.JK', 'MGLV.JK', 'MGNA.JK', 'MGRO.JK', 'MHKI.JK', 'MICE.JK', 'MIDI.JK', 'MIKA.JK', 'MINA.JK', 'MINE.JK', 'MIRA.JK', 'MITI.JK', 'MKAP.JK', 'MKNT.JK', 'MKPI.JK', 'MKTR.JK', 'MLBI.JK', 'MLIA.JK', 'MLPL.JK', 'MLPT.JK', 'MMIX.JK', 'MMLP.JK', 'MNCN.JK', 'MOLI.JK', 'MORA.JK', 'MPIX.JK', 'MPMX.JK', 'MPOW.JK', 'MPPA.JK', 'MPRO.JK', 'MPXL.JK', 'MRAT.JK', 'MREI.JK', 'MSIE.JK', 'MSIN.JK', 'MSJA.JK', 'MSKY.JK', 'MSTI.JK', 'MTDL.JK', 'MTEL.JK', 'MTFN.JK', 'MTLA.JK', 'MTMH.JK', 'MTPS.JK', 'MTRA.JK', 'MTSM.JK', 'MTWI.JK', 'MUTU.JK', 'MYOH.JK', 'MYOR.JK', 'MYTX.JK', 'NAIK.JK', 'NANO.JK', 'NASA.JK', 'NASI.JK', 'NATO.JK', 'NAYZ.JK', 'NCKL.JK', 'NELY.JK', 'NEST.JK', 'NETV.JK', 'NFCX.JK', 'NICE.JK', 'NICK.JK', 'NICL.JK', 'NIKL.JK', 'NINE.JK', 'NIRO.JK', 'NISP.JK', 'NOBU.JK', 'NPGF.JK', 'NRCA.JK', 'NSSS.JK', 'NTBK.JK', 'NUSA.JK', 'NZIA.JK', 'OASA.JK', 'OBAT.JK', 'OBMD.JK', 'OCAP.JK', 'OILS.JK', 'OKAS.JK', 'OLIV.JK', 'OMED.JK', 'OMRE.JK', 'OPMS.JK', 'PACK.JK', 'PADA.JK', 'PADI.JK', 'PALM.JK', 'PAMG.JK', 'PANI.JK', 'PANR.JK', 'PANS.JK', 'PART.JK', 'PBID.JK', 'PBRX.JK', 'PBSA.JK', 'PCAR.JK', 'PDES.JK', 'PDPP.JK', 'PEGE.JK', 'PEHA.JK', 'PEVE.JK', 'PGAS.JK', 'PGEO.JK', 'PGJO.JK', 'PGLI.JK', 'PGUN.JK', 'PICO.JK', 'PIPA.JK', 'PJAA.JK', 'PJHB.JK', 'PKPK.JK', 'PLAN.JK', 'PLAS.JK', 'PLIN.JK', 'PMJS.JK', 'PMMP.JK', 'PMUI.JK', 'PNBN.JK', 'PNBS.JK', 'PNGO.JK', 'PNIN.JK', 'PNLF.JK', 'PNSE.JK', 'POLA.JK', 'POLI.JK', 'POLL.JK', 'POLU.JK', 'POLY.JK', 'POOL.JK', 'PORT.JK', 'POSA.JK', 'POWR.JK', 'PPGL.JK', 'PPRE.JK', 'PPRI.JK', 'PPRO.JK', 'PRAY.JK', 'PRDA.JK', 'PRDL.JK', 'PRIM.JK', 'PSAB.JK', 'PSAT.JK', 'PSDN.JK', 'PSGO.JK', 'PSKT.JK', 'PSSI.JK', 'PTBA.JK', 'PTDU.JK', 'PTIS.JK', 'PTMP.JK', 'PTMR.JK', 'PTPP.JK', 'PTPS.JK', 'PTPW.JK', 'PTRO.JK', 'PTSN.JK', 'PTSP.JK', 'PUDP.JK', 'PURA.JK', 'PURE.JK', 'PURI.JK', 'PWON.JK', 'PYFA.JK', 'PZZA.JK', 'RAAM.JK', 'RAFI.JK', 'RAJA.JK', 'RALS.JK', 'RANC.JK', 'RANS.JK', 'RATU.JK', 'RBMS.JK', 'RCCC.JK', 'RDTX.JK', 'REAL.JK', 'RELF.JK', 'RELI.JK', 'RGAS.JK', 'RICY.JK', 'RIGS.JK', 'RIMO.JK', 'RISE.JK', 'RLCO.JK', 'RMKE.JK', 'RMKO.JK', 'ROCK.JK', 'RODA.JK', 'RONY.JK', 'ROTI.JK', 'RSCH.JK', 'RSGK.JK', 'RUIS.JK', 'RUNS.JK', 'SAFE.JK', 'SAGE.JK', 'SAME.JK', 'SAMF.JK', 'SAPX.JK', 'SATU.JK', 'SBAT.JK', 'SBMA.JK', 'SCCO.JK', 'SCMA.JK', 'SCNP.JK', 'SCPI.JK', 'SDMU.JK', 'SDPC.JK', 'SDRA.JK', 'SEMA.JK', 'SFAN.JK', 'SGER.JK', 'SGRO.JK', 'SHID.JK', 'SHIP.JK', 'SICO.JK', 'SIDO.JK', 'SILO.JK', 'SIMA.JK', 'SIMP.JK', 'SINI.JK', 'SIPD.JK', 'SKBM.JK', 'SKLT.JK', 'SKRN.JK', 'SKYB.JK', 'SLIS.JK', 'SMAR.JK', 'SMBR.JK', 'SMCB.JK', 'SMDM.JK', 'SMDR.JK', 'SMGA.JK', 'SMGR.JK', 'SMIL.JK', 'SMKL.JK', 'SMKM.JK', 'SMLE.JK', 'SMMA.JK', 'SMMT.JK', 'SMRA.JK', 'SMRU.JK', 'SMSM.JK', 'SNLK.JK', 'SOCI.JK', 'SOFA.JK', 'SOHO.JK', 'SOLA.JK', 'SONA.JK', 'SOSS.JK', 'SOTS.JK', 'SOUL.JK', 'SPMA.JK', 'SPRE.JK', 'SPTO.JK', 'SQMI.JK', 'SRAJ.JK', 'SRIL.JK', 'SRSN.JK', 'SRTG.JK', 'SSIA.JK', 'SSMS.JK', 'SSTM.JK', 'STAA.JK', 'STAR.JK', 'STRK.JK', 'STTP.JK', 'SUGI.JK', 'SULI.JK', 'SUNI.JK', 'SUPA.JK', 'SUPR.JK', 'SURE.JK', 'SURI.JK', 'SWAT.JK', 'SWID.JK', 'TALF.JK', 'TAMA.JK', 'TAMU.JK', 'TAPG.JK', 'TARA.JK', 'TAXI.JK', 'TAYS.JK', 'TBIG.JK', 'TBLA.JK', 'TBMS.JK', 'TCID.JK', 'TCPI.JK', 'TDPM.JK', 'TEBE.JK', 'TECH.JK', 'TELE.JK', 'TFAS.JK', 'TFCO.JK', 'TGKA.JK', 'TGRA.JK', 'TGUK.JK', 'TIFA.JK', 'TINS.JK', 'TIRA.JK', 'TIRT.JK', 'TKIM.JK', 'TLDN.JK', 'TLKM.JK', 'TMAS.JK', 'TMPO.JK', 'TNCA.JK', 'TOBA.JK', 'TOOL.JK', 'TOPS.JK', 'TOSK.JK', 'TOTL.JK', 'TOTO.JK', 'TOWR.JK', 'TOYS.JK', 'TPIA.JK', 'TPMA.JK', 'TRAM.JK', 'TRGU.JK', 'TRIL.JK', 'TRIM.JK', 'TRIN.JK', 'TRIO.JK', 'TRIS.JK', 'TRJA.JK', 'TRON.JK', 'TRST.JK', 'TRUE.JK', 'TRUK.JK', 'TRUS.JK', 'TSPC.JK', 'TUGU.JK', 'TYRE.JK', 'UANG.JK', 'UCID.JK', 'UDNG.JK', 'UFOE.JK', 'ULTJ.JK', 'UNIC.JK', 'UNIQ.JK', 'UNIT.JK', 'UNSP.JK', 'UNTD.JK', 'UNTR.JK', 'UNVR.JK', 'URBN.JK', 'UVCR.JK', 'VAST.JK', 'VERN.JK', 'VICI.JK', 'VICO.JK', 'VINS.JK', 'VISI.JK', 'VIVA.JK', 'VKTR.JK', 'VOKS.JK', 'VRNA.JK', 'VTNY.JK', 'WAPO.JK', 'WBSA.JK', 'WEGE.JK', 'WEHA.JK', 'WGSH.JK', 'WICO.JK', 'WIDI.JK', 'WIFI.JK', 'WIIM.JK', 'WIKA.JK', 'WINE.JK', 'WINR.JK', 'WINS.JK', 'WIRG.JK', 'WMPP.JK', 'WMUU.JK', 'WOMF.JK', 'WOOD.JK', 'WOWS.JK', 'WSBP.JK', 'WSKT.JK', 'WTON.JK', 'YELO.JK', 'YOII.JK', 'YPAS.JK', 'YULE.JK', 'YUPI.JK', 'ZATA.JK', 'ZBRA.JK', 'ZINC.JK', 'ZONE.JK', 'ZYRX.JK'
                // (Isi dengan sisa list 963 emiten Anda)
            ];
            
            const batchSize = 20;
            let currentIndex = 0;

            const btnScan = document.getElementById('btn-scan');
            const progressText = document.getElementById('progress-text');
            const statusIndicator = document.getElementById('status-indicator');
            const resultBody = document.getElementById('result-body');
            const timestampText = document.getElementById('timestamp-text');

            // --- Fungsi Fetch/Scan ---
            btnScan.addEventListener('click', async () => {
                if (currentIndex >= allSymbols.length) return;

                btnScan.disabled = true;
                btnScan.innerText = "Scanning...";
                btnScan.classList.replace('bg-blue-600', 'bg-gray-400');

                const currentBatch = allSymbols.slice(currentIndex, currentIndex + batchSize);
                
                try {
                    const response = await fetch('/api/scan', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ symbols: currentBatch })
                    });
                    
                    const matches = await response.json();

                    matches.forEach(r => {
                        const tr = document.createElement('tr');
                        tr.className = "hover:bg-gray-50 transition-colors";
                        
                        const statusClass = r.status === 'CLOSE ABOVE' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700';
                        const changeClass = r.change > 0 ? 'text-green-600' : 'text-red-600';
                        const changeSign = r.change > 0 ? '+' : '';

                        // Perhatikan penambahan atribut data-val="..." untuk mempermudah sorting
                        tr.innerHTML = `
                            <td class="px-6 py-4 font-bold text-gray-900" data-val="${r.simbol}">
                                <div class="flex items-center gap-2">
                                    <span class="text-gray-900">${r.simbol}</span>
                                    <div class="flex gap-1 text-xs">
                                        <a href="https://www.tradingview.com/chart/?symbol=IDX%3A${r.simbol}" target="_blank" class="bg-blue-50 text-blue-600 hover:bg-blue-100 px-2 py-0.5 rounded border border-blue-200 font-semibold" title="Buka di TradingView">TV</a>
                                        <a href="https://stockbit.com/symbol/${r.simbol}/chartbit" target="_blank" class="bg-emerald-50 text-emerald-600 hover:bg-emerald-100 px-2 py-0.5 rounded border border-emerald-200 font-semibold" title="Buka di Stockbit Chartbit">SB</a>
                                    </div>
                                </div>
                            </td>
                            <td class="px-6 py-4" data-val="${r.status}">
                                <span class="px-3 py-1 rounded-full text-xs font-bold ${statusClass}">${r.status}</span>
                            </td>
                            <td class="px-6 py-4 text-right font-mono" data-val="${r.price}">${r.price.toLocaleString('id-ID')}</td>
                            <td class="px-6 py-4 text-right font-bold ${changeClass}" data-val="${r.change}">${changeSign}${r.change.toFixed(2)}%</td>
                            <td class="px-6 py-4 text-right text-gray-600 font-mono" data-val="${r.res}">${r.res.toLocaleString('id-ID')}</td>
                            <td class="px-6 py-4 text-right text-gray-600 font-mono" data-val="${r.vol}">${r.vol.toLocaleString('id-ID')}</td>
                        `;
                        resultBody.appendChild(tr);
                    });

                    currentIndex += currentBatch.length;
                    progressText.innerText = `Scan berjalan... (${currentIndex} / ${allSymbols.length} Emiten)`;

                    if (currentIndex >= allSymbols.length) {
                        statusIndicator.classList.replace('bg-red-500', 'bg-green-500');
                        progressText.innerText = `Scan Selesai! (${currentIndex} / ${allSymbols.length} Emiten)`;
                        btnScan.style.display = 'none'; // Sembunyikan tombol kalau sudah beres
                        
                        // Set Tanggal & Jam Selesai
                        const options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', timeZoneName: 'short' };
                        timestampText.innerText = new Date().toLocaleString('id-ID', options);
                    } else {
                        btnScan.disabled = false;
                        btnScan.innerText = "Next Scan (20 Emiten)";
                        btnScan.classList.replace('bg-gray-400', 'bg-blue-600');
                    }

                } catch (error) {
                    console.error("Error fetching data:", error);
                    alert("Terjadi kesalahan koneksi. Silakan coba Next Scan lagi.");
                    btnScan.disabled = false;
                    btnScan.innerText = "Coba Lagi (Next Scan)";
                    btnScan.classList.replace('bg-gray-400', 'bg-blue-600');
                }
            });

            // --- Fungsi Sorting Table ---
            let sortDirections = [true, true, true, true, true, true]; // Menyimpan arah sortir (Ascending/Descending) per kolom
            function sortTable(colIndex, type) {
                const rows = Array.from(resultBody.querySelectorAll("tr"));
                if (rows.length === 0) return; // Abaikan jika tabel masih kosong

                const isAsc = sortDirections[colIndex];

                rows.sort((a, b) => {
                    let valA = a.cells[colIndex].getAttribute("data-val");
                    let valB = b.cells[colIndex].getAttribute("data-val");

                    if (type === 'num') {
                        valA = parseFloat(valA);
                        valB = parseFloat(valB);
                    } else {
                        valA = valA.toUpperCase();
                        valB = valB.toUpperCase();
                    }

                    if (valA < valB) return isAsc ? -1 : 1;
                    if (valA > valB) return isAsc ? 1 : -1;
                    return 0;
                });

                // Render ulang baris yang sudah diurutkan
                resultBody.innerHTML = "";
                rows.forEach(row => resultBody.appendChild(row));

                // Balikkan arah untuk klik selanjutnya
                sortDirections[colIndex] = !isAsc;
            }

            // --- Fungsi Download HTML ke Gambar ---
            function downloadImage() {
                const element = document.getElementById('capture-area');
                html2canvas(element, {
                    scale: 2,
                    backgroundColor: "#ffffff"
                }).then(canvas => {
                    const link = document.createElement('a');
                    link.download = 'Fractal-Screening-' + new Date().getTime() + '.jpg';
                    link.href = canvas.toDataURL('image/jpeg', 0.9);
                    link.click();
                });
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == '__main__':
    app.run(debug=True)
