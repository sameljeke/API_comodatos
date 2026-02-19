import pandas as pd
from datetime import datetime
from app.extensions import db
from app.models import (
    Instrumento, Comodato, Alumno, Representante, Usuario,
    Medida, EstadoInstrumento
)
from app.utils.generators import CodeGenerator

class ExcelImporter:
    @staticmethod
    def import_from_excel(file_path):
        """Importa datos desde el archivo Excel proporcionado"""
        try:
            # Leer la hoja de comodatos
            df = pd.read_excel(file_path, sheet_name='Relacion de comodato')
            
            # Limpiar y preparar datos
            df = df.rename(columns={
                'DESCRIPCION': 'descripcion',
                'MARCA': 'marca',
                'MODELO': 'modelo',
                'MEDIDA': 'medida_nombre',
                'COLOR': 'color',
                'NUMERO DE SERIAL': 'serial_fabrica',
                'NUMERO DE INVENTARIO': 'serial_inventario',
                'ESTADO': 'estado_nombre',
                'NUCLEO': 'nucleo',
                'ASIGNADO': 'asignado_nombre',
                'COMODATARIO': 'comodatario_nombre',
                'CEDULA DEL COMODATARIO': 'comodatario_cedula',
                'FECHA INICIAL DEL COMODATO': 'fecha_inicio',
                'FECHA FINAL DEL COMODATO': 'fecha_fin',
                'FECHA DE RECEPCIÓN': 'fecha_recepcion',
                'OBSERVACION': 'observaciones'
            })
            
            # Convertir fechas
            date_columns = ['fecha_inicio', 'fecha_fin', 'fecha_recepcion']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
            
            # Procesar cada registro
            results = {
                'instrumentos_importados': 0,
                'comodatos_importados': 0,
                'errores': []
            }
            
            for idx, row in df.iterrows():
                try:
                    # Crear o obtener medida
                    medida = Medida.query.filter_by(
                        nombre=row['medida_nombre']
                    ).first()
                    
                    if not medida:
                        medida = Medida(
                            nombre=row['medida_nombre'],
                            descripcion=f"Medida: {row['medida_nombre']}"
                        )
                        db.session.add(medida)
                        db.session.flush()
                    
                    # Crear instrumento
                    instrumento = Instrumento.query.filter_by(
                        serial_inventario=str(row['serial_inventario'])
                    ).first()
                    
                    if not instrumento:
                        instrumento = Instrumento(
                            descripcion=row['descripcion'],
                            marca=row['marca'],
                            modelo=row['modelo'],
                            id_medida=medida.id_medida,
                            color=row['color'],
                            serial_fabrica=row['serial_fabrica'],
                            serial_inventario=str(row['serial_inventario']),
                            id_estado_instr=1,  # Disponible por defecto
                            observaciones=row.get('observaciones')
                        )
                        db.session.add(instrumento)
                        results['instrumentos_importados'] += 1
                    
                    # Procesar comodato si hay datos
                    if pd.notna(row.get('fecha_inicio')):
                        # Aquí se podría crear el comodato completo
                        # Necesitaríamos crear/alumno, representante y usuario primero
                        pass
                        
                except Exception as e:
                    results['errores'].append({
                        'fila': idx + 1,
                        'error': str(e),
                        'datos': row.to_dict()
                    })
            
            db.session.commit()
            return results
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Error en importación: {str(e)}")