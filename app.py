import math
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def custom_round(value):
    """
    Pembulatan custom:
    - Jika desimal >= 0.5, bulatkan ke atas
    - Jika desimal < 0.5, bulatkan ke bawah
    """
    return math.floor(value + 0.5)

# Fungsi hitung pakar dengan pembulatan custom
def hitung_pakar(tulis, keterampilan, wawancara, kesehatan):
    a = (tulis + keterampilan) / 2
    b = (wawancara + kesehatan + a) / 3
    return b  # Return nilai asli untuk fleksibilitas

# Fungsi fuzzy linear (sama seperti sebelumnya)
def fuzzy_linear(x, x1, x2, naik=True):
    if naik:
        if x <= x1:
            return 0.0
        elif x >= x2:
            return 1.0
        else:
            return (x - x1) / (x2 - x1)
    else:
        if x <= x1:
            return 1.0
        elif x >= x2:
            return 0.0
        else:
            return (x2 - x) / (x2 - x1)

def fuzzify_inputs(tulis, keterampilan, wawancara, kesehatan):
    return {
        'tulis': {
            'lulus': fuzzy_linear(tulis, 25, 75, naik=True),
            'tidak_lulus': fuzzy_linear(tulis, 25, 75, naik=False)
        },
        'keterampilan': {
            'lulus': fuzzy_linear(keterampilan, 25, 75, naik=True),
            'tidak_lulus': fuzzy_linear(keterampilan, 25, 75, naik=False)
        },
        'wawancara': {
            'lulus': fuzzy_linear(wawancara, 55, 75, naik=True),
            'tidak_lulus': fuzzy_linear(wawancara, 55, 75, naik=False)
        },
        'kesehatan': {
            'lulus': fuzzy_linear(kesehatan, 50, 70, naik=True),
            'tidak_lulus': fuzzy_linear(kesehatan, 50, 70, naik=False)
        }
    }

def hitung_z(predikat, alpha):
    if predikat == 'diterima':
        return alpha * 50 + 25
    else:
        return 75 - alpha * 50

rule_output_map = {
    ('lulus', 'lulus', 'lulus', 'lulus'): 'diterima',
    ('lulus', 'lulus', 'lulus', 'tidak_lulus'): 'tidak_diterima',
    ('lulus', 'lulus', 'tidak_lulus', 'lulus'): 'tidak_diterima',
    ('lulus', 'lulus', 'tidak_lulus', 'tidak_lulus'): 'tidak_diterima',
    ('lulus', 'tidak_lulus', 'lulus', 'lulus'): 'diterima',
    ('lulus', 'tidak_lulus', 'lulus', 'tidak_lulus'): 'tidak_diterima',
    ('lulus', 'tidak_lulus', 'tidak_lulus', 'lulus'): 'tidak_diterima',
    ('lulus', 'tidak_lulus', 'tidak_lulus', 'tidak_lulus'): 'tidak_diterima',
    ('tidak_lulus', 'lulus', 'lulus', 'lulus'): 'diterima',
    ('tidak_lulus', 'lulus', 'lulus', 'tidak_lulus'): 'tidak_diterima',
    ('tidak_lulus', 'lulus', 'tidak_lulus', 'lulus'): 'tidak_diterima',
    ('tidak_lulus', 'lulus', 'tidak_lulus', 'tidak_lulus'): 'tidak_diterima',
    ('tidak_lulus', 'tidak_lulus', 'lulus', 'lulus'): 'diterima',
    ('tidak_lulus', 'tidak_lulus', 'lulus', 'tidak_lulus'): 'tidak_diterima',
    ('tidak_lulus', 'tidak_lulus', 'tidak_lulus', 'lulus'): 'tidak_diterima',
    ('tidak_lulus', 'tidak_lulus', 'tidak_lulus', 'tidak_lulus'): 'tidak_diterima'
}

def fuzzy_tsukamoto(tulis, keterampilan, wawancara, kesehatan):
    fuzzy_vals = fuzzify_inputs(tulis, keterampilan, wawancara, kesehatan)
    rules = []
    rule_no = 1

    for t in ['lulus', 'tidak_lulus']:
        for k in ['lulus', 'tidak_lulus']:
            for w in ['lulus', 'tidak_lulus']:
                for h in ['lulus', 'tidak_lulus']:
                    # Tidak menggunakan round() di sini, biarkan nilai asli
                    alpha = min(
                        fuzzy_vals['tulis'][t],
                        fuzzy_vals['keterampilan'][k],
                        fuzzy_vals['wawancara'][w],
                        fuzzy_vals['kesehatan'][h]
                    )
                    status_key = (t, k, w, h)
                    predikat = rule_output_map.get(status_key, 'tidak_diterima')
                    z = hitung_z(predikat, alpha)
                    z = int(-(-z // 1))  # Pembulatan ke atas (ceil)
                    alpha_z = alpha * z  # Tidak menggunakan round() di sini
                    rules.append({
                        'rule': rule_no,
                        'status': [t, k, w, h],
                        'predikat': predikat,
                        'alpha': alpha,
                        'z': z,
                        'alpha_z': alpha_z
                    })
                    rule_no += 1

    total_alpha_z = sum(r['alpha_z'] for r in rules)  # Tidak menggunakan round() di sini
    total_alpha = sum(r['alpha'] for r in rules)  # Tidak menggunakan round() di sini
    hasil_akhir = total_alpha_z / total_alpha if total_alpha != 0 else 0
    status_akhir = 'DITERIMA' if hasil_akhir >= 70 else 'TIDAK DITERIMA'

    return hasil_akhir, status_akhir, rules

def average_rank(values, descending=True):
    """
    Menghitung ranking dengan average rank untuk nilai yang sama (ties)
    """
    # Buat list (index, value) dan urutkan berdasarkan value
    indexed_values = list(enumerate(values))
    indexed_values.sort(key=lambda x: x[1], reverse=descending)
    
    ranks = [0] * len(values)
    current_rank = 1
    
    i = 0
    while i < len(indexed_values):
        # Kumpulkan semua indeks dengan nilai yang sama
        current_value = indexed_values[i][1]
        same_indices = []
        
        # Cari semua nilai yang sama
        j = i
        while j < len(indexed_values) and indexed_values[j][1] == current_value:
            same_indices.append(indexed_values[j][0])  # simpan index asli
            j += 1
        
        # Hitung average rank
        if len(same_indices) == 1:
            # Tidak ada tie, gunakan rank biasa
            avg_rank = current_rank
        else:
            # Ada tie, hitung average rank
            end_rank = current_rank + len(same_indices) - 1
            avg_rank = (current_rank + end_rank) / 2
        
        # Assign rank ke semua indeks dengan nilai sama
        for idx in same_indices:
            ranks[idx] = avg_rank
        
        # Update current_rank untuk grup berikutnya
        current_rank += len(same_indices)
        i = j
    
    return ranks

data_peserta = []

@app.route('/fuzzy', methods=['POST'])
def hitung_fuzzy():
    global data_peserta
    data = request.json

    if isinstance(data, dict):
        nama = data.get('nama', f'Peserta-{len(data_peserta)+1}')
        tulis = data.get('tulis')
        keterampilan = data.get('keterampilan')
        wawancara = data.get('wawancara')
        kesehatan = data.get('kesehatan')

        if None in [tulis, keterampilan, wawancara, kesehatan]:
            return jsonify({'error': 'Input tidak lengkap'}), 400

        data_peserta.append({
            'nama': nama,
            'tulis': tulis,
            'keterampilan': keterampilan,
            'wawancara': wawancara,
            'kesehatan': kesehatan
        })

    hasil = []
    for item in data_peserta:
        nama = item['nama']
        tulis = item['tulis']
        keterampilan = item['keterampilan']
        wawancara = item['wawancara']
        kesehatan = item['kesehatan']

        fuzzy_nilai, status, _ = fuzzy_tsukamoto(tulis, keterampilan, wawancara, kesehatan)
        pakar_nilai = hitung_pakar(tulis, keterampilan, wawancara, kesehatan)

        hasil.append({
            'nama': nama,
            'pakar': pakar_nilai,
            'sistem': fuzzy_nilai,
            'status': status
        })

    # Bulatkan nilai terlebih dahulu, lalu hitung ranking berdasarkan nilai yang sudah dibulatkan
    for item in hasil:
        item['pakar'] = custom_round(item['pakar'])
        item['sistem'] = custom_round(item['sistem'])

    # Hitung ranking berdasarkan nilai yang sudah dibulatkan
    pakar_list = [item['pakar'] for item in hasil]
    sistem_list = [item['sistem'] for item in hasil]

    rank_pakar = average_rank(pakar_list, descending=True)
    rank_sistem = average_rank(sistem_list, descending=True)

    for i, item in enumerate(hasil):
        item['rank_pakar'] = rank_pakar[i]
        item['rank_sistem'] = rank_sistem[i]
        item['di'] = item['rank_pakar'] - item['rank_sistem']
        item['di2'] = item['di'] ** 2

    n = len(hasil)
    total_di2 = sum(item['di2'] for item in hasil)  # Tidak dibulatkan
    spearman_rho = 1 - (6 * total_di2) / (n * (n**2 - 1)) if n > 1 else 1  # Tidak dibulatkan

    return jsonify({
        'hasil': hasil,
        'total_di2': total_di2,
        'spearman_rho': spearman_rho
    })

@app.route('/fuzzy-detail', methods=['POST'])
def fuzzy_detail():
    data = request.json
    tulis = data.get('tulis')
    keterampilan = data.get('keterampilan')
    wawancara = data.get('wawancara')
    kesehatan = data.get('kesehatan')

    if None in [tulis, keterampilan, wawancara, kesehatan]:
        return jsonify({'error': 'Input tidak lengkap'}), 400

    hasil_akhir, status_akhir, rules = fuzzy_tsukamoto(tulis, keterampilan, wawancara, kesehatan)
    return jsonify({
        'hasil_akhir': hasil_akhir,
        'status_akhir': status_akhir,
        'rules': rules
    })

@app.route('/reset', methods=['POST'])
def reset_data():
    global data_peserta
    data_peserta = []
    return jsonify({"status": "reset berhasil"})

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)