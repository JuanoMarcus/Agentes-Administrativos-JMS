"""Arma la entrada JSON del CDP UdeC Espacio Ciencia 2030 (obra gruesa / estructura)."""
import json, copy

UF_HOY, UF_2023 = 41412.34, 36071.45
F = round(UF_HOY / UF_2023, 5)  # reajuste por variación de la UF
cdp = json.load(open('/tmp/cp/cdp.json'))
Q0 = {p['item']: p.get('cantidad') for p in cdp['partidas']}
Q0.update({'2.2': 700, '2.3': 627.6, '2.5': 104.55, '2.6': 10.2635, '2.7': 998.78, '2.8': 13477.59,
           '2.9': 171.893, '2.11': 487.8, '2.12': 657.4, '2.13': 657.4, '2.15': 11368.12, '2.24': 10418.15})


def expr(v):
    return str(v)[1:] if isinstance(v, str) and v.startswith('=') else str(v)


def reaj(v):
    return f"=({expr(v)})*{F}"


def esc(v, r):
    return f"=({expr(v)})*{r:.6f}" if abs(r - 1) > 1e-9 else (v if not isinstance(v, str) else v)


def reuse(k, qnew, cambios=None, quitar=()):
    """APU del CDP-001 ítem k, escalado a la nueva cantidad y con precios reajustados por UF."""
    a = copy.deepcopy(cdp['apu'][k])
    r = qnew / float(Q0[k])
    out = {'materiales': [], 'mano_obra': [], 'equipos': []}
    for ln in a.get('materiales', []):
        if ln.get('precio') is None or ln['descripcion'] in quitar:
            continue
        d = dict(descripcion=ln['descripcion'], unidad=ln['unidad'], cantidad=esc(ln['cantidad'], r),
                 perdida=ln.get('perdida', 0), precio=reaj(ln['precio']))
        if cambios and ln['descripcion'] in cambios:
            d.update(cambios[ln['descripcion']])
        out['materiales'].append(d)
    for ln in a.get('mano_obra', []):
        out['mano_obra'].append(dict(especialidad=ln['especialidad'], cantidad=esc(ln['cantidad'], r),
                                     costo_hd=reaj(ln['costo_hd'])))
    for ln in a.get('equipos', []):
        if ln.get('costo') is None:
            continue
        out['equipos'].append(dict(descripcion=ln['descripcion'], unidad=ln['unidad'], cantidad=esc(ln['cantidad'], r),
                                   costo=reaj(ln['costo']), vida_util=ln.get('vida_util', 1)))
    return out


def mo(esp, hd, costo):
    return dict(especialidad=esp, cantidad=hd, costo_hd=reaj(costo))


# ---------------- Cantidades (todas trazables en la hoja Cubicación) ----------------
L_FUND = 131.0      # m de muro/zapata corrida: 261,7 m de líneas capa 18_FUND en planta (doble línea) / 2
B_ZAP = 1.35        # ancho medio zapata corrida (secciones 1-16: 1,20 / 1,40 / 1,60 m)
cub = []


def c(item, elemento, plano, veces=1, largo=None, ancho=None, alto=None, cantidad=None, obs=None):
    if cantidad is not None and veces != 1:  # la planilla no multiplica 'veces' cuando hay cantidad directa
        cantidad, veces = f"={veces}*({expr(cantidad)})", 1
    cub.append({k: v for k, v in dict(item=item, elemento=elemento, plano=plano, veces=veces, largo=largo, ancho=ancho,
                                       alto=alto, cantidad=cantidad, obs=obs).items() if v is not None})


P001 = 'C-ECU-1904-001 Rev A'
IFC = 'IFC arquitectura Oct-2026'
# 1.0
c('1.7', 'Huella del edificio (rectángulo ejes 1-6 / C-L)', P001, 1, 25.3, 18.4, obs='Medido en planta de fundaciones')
c('1.8', 'Despeje y limpieza de la huella', P001, 1, 25.3, 18.4)
# 2.0 movimiento de tierras
c('2.1', 'Zanjas fundación corrida (ancho 1,35 + 2×0,20 sobreancho)', P001, 1, L_FUND, B_ZAP + 0.40, 1.25,
  obs='Sello -1,20 (N.S.F.) + 0,05 emplantillado. Secciones 1-16')
c('2.1', 'Excavación zapatas aisladas bajo PD1 (supuesto 1,2×1,2 + sobreancho)', P001, 10, 1.6, 1.6, 1.25,
  obs='SUPUESTO: dimensiones de zapata PD1 no leídas en plano')
c('2.2', 'Excavación bajo radier (radier 0,12 + base 0,15)', IFC, 1, None, None, 0.27, cantidad='=266.5*0.27',
  obs='Área radier 266,5 m² (losas hormigón Planta Baja en IFC)')
c('2.3', 'Mejoramiento bajo zapata corrida e=0,30 (arena Bío Bío compactada 80% DR)', P001, 1, L_FUND, B_ZAP + 0.40, 0.30,
  obs='SUPUESTO e=0,30: plano indica "mejoramiento según mecánica de suelos"')
c('2.4', 'Excavación total fundaciones', P001, 1, cantidad='=131*1.75*1.25+10*1.6*1.6*1.25')
c('2.4', 'Menos: emplantillado', P001, -1, cantidad='=131*1.45*0.05+10*1.3*1.3*0.05')
c('2.4', 'Menos: zapatas corridas', P001, -1, L_FUND, B_ZAP, 0.50)
c('2.4', 'Menos: zapatas aisladas PD1', P001, -10, 1.2, 1.2, 0.50)
c('2.4', 'Menos: muros de fundación bajo terreno', P001, -1, L_FUND, 0.15, 0.70)
c('2.4', 'Menos: pedestales PD1-PD4', P001, -32, 0.35, 0.35, 0.70)
c('2.4', 'Menos: mejoramiento (ya relleno)', P001, -1, L_FUND, B_ZAP + 0.40, 0.30, obs='El mejoramiento va en el ítem 2.3')
c('2.5', 'Base estabilizada CBR>60% e=0,15 + polietileno 0,2 mm', IFC, 1, cantidad=266.5, obs='Detalle radier plano 001')
# 3.0 hormigones fundación
c('3.1', 'Emplantillado zapata corrida e=0,05', P001, 1, L_FUND, B_ZAP + 0.10, 0.05)
c('3.1', 'Emplantillado zapatas aisladas e=0,05', P001, 10, 1.3, 1.3, 0.05)
c('3.2', 'Zapata corrida b=1,35 (prom.) h=0,50', P001, 1, L_FUND, B_ZAP, 0.50, obs='Secciones 1-16 ESC 1:50')
c('3.2', 'Zapatas aisladas PD1 1,2×1,2×0,5 (supuesto)', P001, 10, 1.2, 1.2, 0.50, obs='SUPUESTO')
c('3.2', 'Muro de fundación e=0,15 h=0,70', P001, 1, L_FUND, 0.15, 0.70)
c('3.2', 'Pedestales PD1(10) PD2(4) PD3(12) PD4(6) 0,35×0,35×0,70', P001, 32, 0.35, 0.35, 0.70,
  obs='Conteo de rótulos en planta; sección media 0,25-0,45 m')
c('3.3', 'Moldaje caras zapata corrida', P001, 2, L_FUND, None, 0.50)
c('3.3', 'Moldaje zapatas aisladas', P001, 10, 4.8, None, 0.50)
c('3.3', 'Moldaje muro de fundación (2 caras)', P001, 2, L_FUND, None, 0.70)
c('3.3', 'Moldaje pedestales', P001, 32, 1.40, None, 0.70)
c('3.4', 'Fundación corrida: SØ10@14 + IØ12@14 L=1,90; VØ10@14; HØ8@14; long. 2Ø12+4Ø10 ≈ 35 kg/m + 10% traslapos',
  P001, 1, cantidad='=131*35*1.10', obs='Cuantía derivada de las secciones tipo')
c('3.4', 'Zapatas aisladas 80 kg/m³ (supuesto)', P001, 1, cantidad='=7.2*80', obs='SUPUESTO')
c('3.4', 'Pedestales 150 kg/m³ (supuesto)', P001, 1, cantidad='=2.744*150', obs='SUPUESTO')
c('3.5', 'Radier e=12 cm G20 + malla ACMA C-139', IFC, 1, cantidad=266.5)
# 4.0 muros y losas HA en elevación
c('4.1', 'Muros HA e=15 Planta Baja (13 muros, 52,8 m)', IFC, 1, cantidad=23.03, obs='Volumen calculado desde el IFC')
c('4.1', 'Muros HA e=15 1er piso (2 muros, 7,3 m)', IFC, 1, cantidad=1.63)
c('4.2', 'Moldaje muros HA (2 caras, 186,5 m² por cara)', IFC, 2, cantidad=186.5)
c('4.3', 'Armadura muros HA 110 kg/m³ (doble malla Ø10@15, supuesto)', IFC, 1, cantidad='=24.66*110', obs='SUPUESTO cuantía')
c('4.4', 'Sobrelosa HA e≈5 cm sobre entrepiso madera 2° nivel', IFC, 1, cantidad=228.0,
  obs='IFC: losa "Hormigón Armado" 228 m², 11,0 m³. Confirmar con estructura')
# 5.0 estructura metálica
c('5.1', 'PM1 cañería 8" Ø219,1×8,18 (42,55 kg/m)', IFC, 1, 55.6, None, None, cantidad='=55.6*42.55', obs='12 pilares, 55,6 m (IFC)')
c('5.2', 'VM1 IPE 300 (42,2 kg/m) 1er y 2° piso', IFC, 1, cantidad='=81.0*42.2', obs='5 vigas, 81,0 m (IFC). SUPUESTO perfil')
c('5.2', 'Vigas CJ 150/100/4 (15,2 kg/m)', IFC, 1, cantidad='=22.5*15.2', obs='2 vigas, 22,5 m (IFC)')
c('5.3', 'VR vigas reticuladas h=101,5 cm (cuerdas CJ100/100/3, diag. CJ50/50/4) ≈27 kg/m', '002-E / IFC', 1,
  cantidad='=55*27', obs='55 m (IFC 2° piso). SUPUESTO peso por metro')
c('5.4', 'Escalera caracol y elementos metálicos varios', IFC, 1, cantidad='=0.48*7850', obs='IFC: 8 partes acero 0,48 m³. Verificar')
c('5.5', 'Placas base, atiesadores, pernos y conexiones (10% de 5.1-5.4)', '007-A / 008-A', 1,
  cantidad='=0.10*(55.6*42.55+81*42.2+22.5*15.2+55*27+0.48*7850)', obs='SUPUESTO 10%')
c('5.6', 'Cerchas CH1-CH6: cuerdas C150/50/3 (5,89 kg/m) ×2×24,4 m + diag./mont. 2L40/40/3 (3,63 kg/m) ×36,6 m', '003-E', 11,
  cantidad='=(2*24.4*5.89+36.6*3.63)', obs='11 cerchas (rótulos CH en planta techumbre), luz 24,4 m (IFC)')
c('5.6', 'Costaneras CA150/50/15/3 (6,59 kg/m) @1,0 m', '003-E', 1, cantidad='=25*17.4*6.59', obs='SUPUESTO separación 1 m')
c('5.6', 'Separadores, colgadores, arriostramientos y placas techumbre (8%)', '003-E', 1,
  cantidad='=0.08*(11*(2*24.4*5.89+36.6*3.63)+25*17.4*6.59)', obs='SUPUESTO 8%')
c('5.7', 'Elementos decorativos VM2/PM2 CJ100/100/4 (12,06 kg/m)', '009-A / IFC', 1, cantidad='=(1110.9+63.0)*12.06',
  obs='IFC: 303 vigas 1.110,9 m + 12 pilares 63,0 m')
# 6.0 madera
c('6.1', 'Pilares MLE PML1 215×215 / PML2 215×400', IFC, 1, cantidad='=6.47+0.58', obs='24 pilares (IFC)')
c('6.1', 'Vigas MLE VML1 150×450, VML2 115×300, VML3/4 115×215 y entramado de piso', IFC, 1,
  cantidad='=12.48+2.88+2.91+1.44+1.64+0.51', obs='161 vigas (IFC)')
c('6.2', 'Herrajes de acero A270ES zincado y fijaciones (Rothoblaas) 30 kg/m³ MLE', '008-A', 1, cantidad='=28.91*30',
  obs='SUPUESTO cuantía')
c('6.3', 'Tabiques estructurales 2×6" (Planta Baja + 1er piso)', IFC, 1, cantidad='=77.7+61.7+62.5', obs='Área de una cara (IFC)')
c('6.4', 'Tablero estructural de entrepiso 2° nivel', IFC, 1, cantidad=210.0, obs='IFC: losa madera 50 mm, 210 m². SUPUESTO OSB 15 mm')
c('6.5', 'Gradas y contrahuellas madera e=32 mm', '004-C / IFC', 1, cantidad='=54.9+63.7', obs='Huellas + contrahuellas (IFC)')
c('6.6', 'Elementos decorativos de madera (listones)', '009-A / IFC', 1, cantidad=20.15, obs='IFC: 541 piezas, 1.386 m')

# ---------------- Partidas ----------------
C1, C2, C3, C4, C5, C6 = ('1.0 INSTALACIÓN DE FAENA Y OBRAS PREVIAS', '2.0 MOVIMIENTO DE TIERRAS', '3.0 FUNDACIONES',
                          '4.0 HORMIGÓN ARMADO EN ELEVACIÓN', '5.0 ESTRUCTURA METÁLICA', '6.0 ESTRUCTURA DE MADERA')
partidas = [
    dict(item='1.1', capitulo=C1, descripcion='Oficina, bodegas y pañol', unidad='gl', cantidad=1, et='ET 2.2'),
    dict(item='1.2', capitulo=C1, descripcion='Instalación sanitaria provisoria', unidad='gl', cantidad=1, et='ET 2.2'),
    dict(item='1.3', capitulo=C1, descripcion='Empalme eléctrico provisorio', unidad='gl', cantidad=1, et='ET 2.2'),
    dict(item='1.4', capitulo=C1, descripcion='Cierros provisorios y señalización', unidad='gl', cantidad=1, et='ET 1.8'),
    dict(item='1.5', capitulo=C1, descripcion='Acreditación de trabajadores, maquinarias y equipos', unidad='gl', cantidad=1, et='ET 1.5'),
    dict(item='1.6', capitulo=C1, descripcion='Revisión externa de cálculo', unidad='gl', por_mandante='UdeC', et='—'),
    dict(item='1.7', capitulo=C1, descripcion='Trazados y nivelaciones', unidad='m2', et='ET 2.3'),
    dict(item='1.8', capitulo=C1, descripcion='Despeje y limpieza del terreno', unidad='m2', et='ET 2.4'),
    dict(item='2.1', capitulo=C2, descripcion='Excavación de fundaciones (incl. sobreancho)', unidad='m3', et='ET 3.2'),
    dict(item='2.2', capitulo=C2, descripcion='Excavación bajo radier', unidad='m3', et='ET 3.2'),
    dict(item='2.3', capitulo=C2, descripcion='Mejoramiento de suelo bajo fundaciones (arena compactada)', unidad='m3', et='ET 4.2'),
    dict(item='2.4', capitulo=C2, descripcion='Rellenos laterales compactados', unidad='m3', et='ET 4.2 - 4.3'),
    dict(item='2.5', capitulo=C2, descripcion='Base estabilizada e=15 cm + polietileno 0,2 mm bajo radier', unidad='m2', et='ET 4.3'),
    dict(item='3.1', capitulo=C3, descripcion='Emplantillado G10 e=5 cm', unidad='m3', et='ET 5.1'),
    dict(item='3.2', capitulo=C3, descripcion='Hormigón G25 fundaciones (zapatas, muros de fundación, pedestales)', unidad='m3', et='ET 6'),
    dict(item='3.3', capitulo=C3, descripcion='Moldajes de fundación (incl. descimbre)', unidad='m2', et='ET 7'),
    dict(item='3.4', capitulo=C3, descripcion='Armadura A630-420H fundaciones', unidad='kg', et='ET 8'),
    dict(item='3.5', capitulo=C3, descripcion='Radier e=12 cm G20 + malla ACMA C-139 (incl. curado)', unidad='m2', et='ET 6 / plano 001'),
    dict(item='4.1', capitulo=C4, descripcion='Hormigón G25 muros HA e=15 cm', unidad='m3', et='ET 6'),
    dict(item='4.2', capitulo=C4, descripcion='Moldaje muros HA (incl. descimbre)', unidad='m2', et='ET 7'),
    dict(item='4.3', capitulo=C4, descripcion='Armadura A630-420H muros', unidad='kg', et='ET 8'),
    dict(item='4.4', capitulo=C4, descripcion='Sobrelosa HA e=5 cm sobre entrepiso de madera', unidad='m2', et='IFC / por confirmar'),
    dict(item='5.1', capitulo=C5, descripcion='Pilares PM1 cañería 8" A270ES', unidad='kg', et='ET 9'),
    dict(item='5.2', capitulo=C5, descripcion='Vigas metálicas VM1 y CJ 150/100/4', unidad='kg', et='ET 9'),
    dict(item='5.3', capitulo=C5, descripcion='Vigas reticuladas VR h=101,5 cm 2° nivel', unidad='kg', et='ET 9'),
    dict(item='5.4', capitulo=C5, descripcion='Escalera caracol y elementos metálicos varios', unidad='kg', et='ET 9'),
    dict(item='5.5', capitulo=C5, descripcion='Placas, atiesadores, pernos y conexiones', unidad='kg', et='ET 9.10'),
    dict(item='5.6', capitulo=C5, descripcion='Estructura de techumbre: cerchas y costaneras', unidad='kg', et='ET 9 / 11'),
    dict(item='5.7', capitulo=C5, descripcion='Estructura elementos decorativos metálicos', unidad='kg', et='ET 9 / plano 009'),
    dict(item='6.1', capitulo=C6, descripcion='Pilares y vigas MLE pino radiata C24 mle24h, CCA 4,0 kg/m³', unidad='m3', et='ET 10.2'),
    dict(item='6.2', capitulo=C6, descripcion='Herrajes y fijaciones de madera', unidad='kg', et='ET 10.3 - 10.8'),
    dict(item='6.3', capitulo=C6, descripcion='Tabiques estructurales de madera 2×6"', unidad='m2', et='ET 10 / plano 010'),
    dict(item='6.4', capitulo=C6, descripcion='Tablero estructural de entrepiso OSB 15 mm', unidad='m2', et='IFC / por confirmar'),
    dict(item='6.5', capitulo=C6, descripcion='Gradas de madera e=32 mm', unidad='m2', et='Plano 004'),
    dict(item='6.6', capitulo=C6, descripcion='Elementos decorativos de madera', unidad='m3', et='Plano 009'),
]

# ---------------- APU ----------------
q = {}  # cantidades (para escalar APU) calculadas aquí igual que en la cubicación
q['1.7'] = q['1.8'] = 25.3 * 18.4
q['2.1'] = 131 * 1.75 * 1.25 + 10 * 1.6 * 1.6 * 1.25
q['2.2'] = 266.5 * 0.27
q['2.3'] = 131 * 1.75 * 0.30
q['2.4'] = (q['2.1'] - (131 * 1.45 * 0.05 + 10 * 1.3 * 1.3 * 0.05) - 131 * 1.35 * 0.5 - 10 * 1.2 * 1.2 * 0.5
            - 131 * 0.15 * 0.7 - 32 * 0.35 * 0.35 * 0.7 - q['2.3'])
q['2.5'] = 266.5
q['3.1'] = 131 * 1.45 * 0.05 + 10 * 1.3 * 1.3 * 0.05
q['3.2'] = 131 * 1.35 * 0.5 + 10 * 1.2 * 1.2 * 0.5 + 131 * 0.15 * 0.7 + 32 * 0.35 * 0.35 * 0.7
q['3.3'] = 2 * 131 * 0.5 + 10 * 4.8 * 0.5 + 2 * 131 * 0.7 + 32 * 1.4 * 0.7
q['3.4'] = 131 * 35 * 1.1 + 7.2 * 80 + 2.744 * 150
q['3.5'] = 266.5
q['4.1'] = 24.66
q['4.2'] = 373.0
q['4.3'] = 24.66 * 110
q['4.4'] = 228.0
k51 = 55.6 * 42.55; k52 = 81 * 42.2 + 22.5 * 15.2; k53 = 55 * 27; k54 = 0.48 * 7850
q['5.1'], q['5.2'], q['5.3'], q['5.4'] = k51, k52, k53, k54
q['5.5'] = 0.10 * (k51 + k52 + k53 + k54)
cer = 11 * (2 * 24.4 * 5.89 + 36.6 * 3.63) + 25 * 17.4 * 6.59
q['5.6'] = cer * 1.08
q['5.7'] = (1110.9 + 63.0) * 12.06
q['6.1'] = 28.91; q['6.2'] = 28.91 * 30; q['6.3'] = 201.9; q['6.4'] = 210.0; q['6.5'] = 118.6; q['6.6'] = 20.15

G25 = {'Hormigón H-20': dict(descripcion='Hormigón G25 premezclado (precio H-20 CDP-001; cotizar G25)')}
apu = {
    '1.1': reuse('1.1', 1), '1.2': reuse('1.2', 1), '1.3': reuse('1.3', 1), '1.4': reuse('1.4', 1), '1.5': reuse('1.6', 1),
    '1.7': reuse('2.2', q['1.7']),
    '1.8': reuse('1.5', 1),
    '2.1': reuse('2.3', q['2.1']),
    '2.2': reuse('2.5', q['2.2']),
    '2.4': reuse('2.11', q['2.4']),
    '3.1': reuse('2.6', q['3.1'], {'Hormigón 170 kg/m2': dict(descripcion='Hormigón G10 emplantillado')}),
    '3.2': reuse('2.9', q['3.2'], G25),
    '3.3': reuse('2.7', q['3.3']),
    '3.4': reuse('2.8', q['3.4']),
    '4.1': reuse('2.9', q['4.1'], G25),
    '4.2': reuse('2.7', q['4.2']),
    '4.3': reuse('2.8', q['4.3']),
    '5.1': reuse('2.15', q['5.1']), '5.2': reuse('2.15', q['5.2']), '5.3': reuse('2.15', q['5.3']),
    '5.4': reuse('2.15', q['5.4']), '5.5': reuse('2.15', q['5.5']), '5.7': reuse('2.15', q['5.7']),
    '5.6': reuse('2.24', q['5.6']),
    '6.2': reuse('2.15', q['6.2']),
}
# 1.8 despeje: el APU 1.5 CDP-001 (destronque) se usa como global; ajustar
# 2.3 mejoramiento = APU rellenos 2.11 + arena
a = reuse('2.11', q['2.3'])
a['materiales'] = [dict(descripcion='Arena (mejoramiento, esponjamiento 1,25)', unidad='m3', cantidad=f"={q['2.3']:.3f}*1.25",
                        perdida=0.05, precio=reaj(10000))]
apu['2.3'] = a
# 2.5 base estabilizada + polietileno: APU 2.12 sin poliestireno ni ripio, base e=0,15
a = reuse('2.12', q['2.5'], quitar=('Cama ripio (50% chancado)', 'Poliestireno extruido (100 mm)'))
for m_ in a['materiales']:
    if m_['descripcion'].startswith('Base estabilizada'):
        m_.update(descripcion='Base estabilizada CBR>60% e=0,15', cantidad='=266.5*0.15', precio=reaj(16000))
    if m_['descripcion'].startswith('Polietileno'):
        m_.update(descripcion='Polietileno 0,2 mm (rollo)', cantidad=f"=16*266.5/657.4")
apu['2.5'] = a
# 3.5 radier e=12 G20 + C-139: APU 2.13 con espesor 12 cm y malla C-139
a = reuse('2.13', q['3.5'])
for m_ in a['materiales']:
    if m_['descripcion'] == 'Hormigón H-20':
        m_.update(descripcion='Hormigón G20 radier e=12 cm', cantidad='=266.5*0.12')
    if m_['descripcion'].startswith('Malla'):
        m_.update(descripcion='Malla ACMA C-139 2,6×5', cantidad='=266.5/(2.6*5)', precio=reaj(40800))
apu['3.5'] = a
# 4.4 sobrelosa e=5: mismo APU de radier, espesor 5 cm
a = reuse('2.13', q['4.4'])
for m_ in a['materiales']:
    if m_['descripcion'] == 'Hormigón H-20':
        m_.update(descripcion='Hormigón G25 sobrelosa e=5 cm (precio H-20 CDP-001)', cantidad='=228*0.05')
    if m_['descripcion'].startswith('Malla'):
        m_.update(descripcion='Malla ACMA C-139 2,6×5 (supuesto)', cantidad='=228/(2.6*5)', precio=reaj(40800))
apu['4.4'] = a
# 6.1 MLE: precio de material y rendimientos del Generador de Precios CYPE Chile (EMV110)
apu['6.1'] = dict(
    materiales=[dict(descripcion='Madera laminada encolada GL-24h, protección NP5-NP6, trabajada en taller (CYPE Chile EMV110)',
                     unidad='m3', cantidad=28.91, perdida=0.03, precio='=945976.47/1.02-116730.9-60112.34')],
    mano_obra=[mo('Maestro (ra)', '=28.91*7.682/8', 30000), mo('Ayudante', '=28.91*3.841/8', 20000),
               mo('Supervisor', '=28.91*0.10', 83333.33)],
    equipos=[dict(descripcion='Grúa telescópica 30 t (CYPE: 3,203 h/m³ × $36.444/h)', unidad='día', cantidad='=28.91*3.203/8',
                  costo='=36444.24*8', vida_util=1)])
# 6.3 tabique estructural 2x6 @ 50 cm (pie derecho, soleras, diagonales ≈ 3,2 ml/m²)
apu['6.3'] = dict(
    materiales=[dict(descripcion='Pino 2×6" × 4,8 m seco cepillado (mad.1006)', unidad='pz', cantidad='=201.9*3.2/4.8', perdida=0.10,
                     precio=reaj(19990)),
                dict(descripcion='Clavos y tornillos HBS', unidad='kg', cantidad='=201.9*0.05', perdida=0.05, precio=reaj(3000))],
    mano_obra=[mo('Maestro (ra)', '=201.9*0.08', 30000), mo('Ayudante', '=201.9*0.08', 20000)],
    equipos=[])
apu['6.4'] = dict(
    materiales=[dict(descripcion='Tablero OSB 15 mm estructural 1,2×2,4 (mad.1011)', unidad='pl', cantidad='=210/(1.2*2.4)', perdida=0.08,
                     precio=reaj(37990)),
                dict(descripcion='Tornillos y clavos', unidad='kg', cantidad='=210*0.03', perdida=0.05, precio=reaj(3000))],
    mano_obra=[mo('Maestro (ra)', '=210*0.04', 30000), mo('Ayudante', '=210*0.04', 20000)], equipos=[])
apu['6.5'] = dict(
    materiales=[dict(descripcion='Tablero terciado estructural 15 mm (mad.1009), 2 capas ≈ e=30 mm (proxy de e=32)', unidad='pl',
                     cantidad='=2*118.6/(1.2*2.4)', perdida=0.10, precio=reaj(22400)),
                dict(descripcion='Tornillos y adhesivo', unidad='kg', cantidad='=118.6*0.05', perdida=0.05, precio=reaj(3000))],
    mano_obra=[mo('Maestro (ra)', '=118.6*0.10', 30000), mo('Ayudante', '=118.6*0.10', 20000)], equipos=[])
apu['6.6'] = dict(
    materiales=[dict(descripcion='Pino 2×6" × 4,8 m seco cepillado (0,02716 m³/pz) (mad.1006)', unidad='pz', cantidad='=20.15/0.02716',
                     perdida=0.10, precio=reaj(19990))],
    mano_obra=[mo('Maestro (ra)', '=20.15*2.0', 30000), mo('Ayudante', '=20.15*2.0', 20000)], equipos=[])

for k, v in q.items():
    pass

entrada = dict(
    codigo='CDP-UDEC-1904', fecha='2026-11-26', revision='v_001 (A)',
    proyecto='EDIFICIO ESPACIO CIENCIA 2030 — UNIVERSIDAD DE CONCEPCIÓN (obra gruesa: estructura)',
    mandante='Universidad de Concepción', direccion='Campus Concepción (por confirmar)', email='jsmarcus@jms.cl', contacto='41-2282221',
    documentos_base=('Planos C-ECU-1904-001 A, 002 E, 003 E, 004 C, 005 C, 006 C, 007 A, 008 A, 009 A, 010 A; '
                     'EETT 1904-EETT-ECU Rev A (24-11-2026); arquitectura A.15.1, A.15.9, A.15.10; modelo IFC Espacio Ciencia 2030 (oct-2026)'),
    superficie_total=494.5,
    uf=UF_HOY, fecha_uf='26-11-2026', fuente_uf='SII, valor UF 26-11-2026 ($41.412,34)',
    gastos_generales=0.25, utilidades=0.12, contingencia=0.0, iva=0.19, leyes_sociales=0.28,
    nota_gg='25 %, criterio JMS CDP-001 (2023). Confirmar', nota_ut='12 %, criterio JMS CDP-001 (2023). Confirmar',
    nota_ls='28 %, criterio APU CDP-001 (2023)',
    fuente_mano_obra=f'Costos HD del CDP-001 (jun-2023) × {F} (variación UF 16-06-2023 → 26-11-2026), escritos en cada línea de APU',
    partidas=partidas, cubicacion=cub, materiales=cdp['materiales'], mano_obra=cdp['mano_obra'], apu=apu,
    referencias=cdp['referencias'] + [
        dict(nombre='Generador de Precios CYPE Chile — EMV110 viga de madera laminada encolada ($945.976/m³)',
             url='http://www.chile.generadordeprecios.info/rehabilitacion/Estructuras/Madera/Vigas/Viga_de_madera_laminada_encolada_0_0_0_0_2_2.html'),
        dict(nombre='SII — valor UF 2026', url='https://www.sii.cl/valores_y_fechas/uf/uf2026.htm')],
    observaciones=[
        'Alcance: obra gruesa estructural (fundaciones, hormigón armado, acero y madera) según planos C-ECU-1904 y EETT estructural. '
        'Excluye cubierta, revestimientos, terminaciones, instalaciones y obras exteriores.',
        f'Precios: APU del CDP-001 JMS (jun-2023) reajustados por variación de la UF (factor {F}). Referenciales: reemplazar por cotizaciones.',
        'MLE: precio del Generador de Precios CYPE Chile (EMV110), no reajustado. Cotizar con fabricante (Hilam/Arauco u otro).',
        'Hormigón G25: se usa el precio H-20 del CDP-001; cotizar G25 premezclado.',
        'Cantidades de muros HA, madera, acero y losas medidas desde el modelo IFC de arquitectura y contrastadas con los planos de estructura; '
        'fundaciones y pedestales medidos en el plano 001.'],
    notas=[
        'SUPUESTOS marcados en la hoja Cubicación (columna Obs.).',
        'Superficie de referencia 494,5 m² = radier PB 266,5 m² + entrepiso 2° nivel 228 m² (IFC); solo para indicador UF/m².',
        'Excedentes de excavación incluidos en el APU de excavación (criterio CDP-001).',
        'Pendientes sin precio: geotextil Propex 401, pintura intumescente (ET 9.19, si aplica), revisión externa de cálculo (por mandante).'],
    firma='JMS Ingenieros Consultores — estimación referencial; la responsabilidad técnica es del ingeniero a cargo',
)
json.dump(entrada, open('/tmp/udec/udec_in.json', 'w'), ensure_ascii=False, indent=1)
print('F =', F)
for k in sorted(q, key=lambda s: [int(x) for x in s.split('.')]):
    print(k, round(q[k], 2))
