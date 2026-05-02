NOMBRES_FEMENINOS = {
    'ANA', 'ANGELA', 'CAMILA', 'CLAUDIA', 'DANIELA', 'DIANA', 'GABRIELA',
    'ISABELLA', 'JULIANA', 'LAURA', 'LUISA', 'LUZ', 'MANUELA', 'MARIA',
    'MARIANA', 'MARTA', 'PAOLA', 'PATRICIA', 'SALOME', 'SARA', 'SOFIA',
    'VALENTINA', 'YULIANA', 'LINA', 'LUCIANA',
}

NOMBRES_MASCULINOS = {
    'ALEJANDRO', 'ANDRES', 'CARLOS', 'DANIEL', 'DAVID', 'EMILIANO', 'JORGE',
    'JUAN', 'MATEO', 'MIGUEL', 'NICOLAS', 'PABLO', 'RICARDO', 'SAMUEL',
    'SANTIAGO', 'SEBASTIAN', 'TOMAS', 'FARID', 'SLAYDER', 'JONATAN',
    'JADER', 'ANDERSON', 'YESID', 'JESUS',
}


def inferir_genero_por_nombre(nombres):
    if not nombres:
        return 'M'

    primer_nombre = str(nombres).strip().split()[0].upper()
    if primer_nombre in NOMBRES_FEMENINOS:
        return 'F'
    if primer_nombre in NOMBRES_MASCULINOS:
        return 'M'
    return 'F' if primer_nombre.endswith('A') else 'M'
