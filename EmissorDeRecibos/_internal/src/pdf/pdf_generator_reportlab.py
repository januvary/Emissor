#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReportLab PDF Generator for SESAP Mandado Judicial
Replaces xhtml2pdf with pure Python solution

REFACTORED: Now uses modular architecture with separate config and styles.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from io import BytesIO, BufferedWriter
import sys

from svglib.svglib import svg2rlg

from src.utils.error_handler import ErrorHandler, ErrorContext, ErrorLevel
from src.pdf.pdf_config import PDFConfig, PDFDataContext
from src.pdf.pdf_styles import PDFStyleManager, _DrawingFlowable

# ============================================================================
# TABLE BUILDERS
# ============================================================================


class HeaderTableBuilder:
    """Builder para tabela de cabeçalho com logo e texto"""

    def __init__(self, config: PDFConfig, styles: PDFStyleManager):
        self.config = config
        self.styles = styles

    def build(self) -> Table:
        """Cria tabela de cabeçalho"""
        # Tentar carregar logo SVG
        logo_drawing = self._get_logo_drawing()

        # Conteúdo de texto
        text_content = (
            "<b>PREFEITURA DA ESTÂNCIA BALNEÁRIA DE PRAIA GRANDE</b><br/><br/>"
            f'<font size="{self.config.FONT_SIZE_LARGE}"><b>SECRETARIA MUNICIPAL DE SAÚDE PÚBLICA</b></font><br/>'
            f'<font size="{self.config.FONT_SIZE_NORMAL}"><b>Av. Pres. Kennedy, 8850 - Nova Mirim, Praia Grande - SP, CEP 11705-005</b></font>'
        )
        text = Paragraph(text_content, self.styles.create_header_medium_style())

        if logo_drawing:
            # Linha única: logo e texto juntos
            data = [[logo_drawing, text]]
            table = Table(
                data,
                colWidths=[
                    self.config.total_width * self.config.COL_LOGO_WIDTH,
                    self.config.total_width * self.config.COL_TEXT_WIDTH,
                ],
            )

            table.setStyle(
                TableStyle(
                    [
                        ("BORDER", (0, 0), (-1, -1), 1, self.config.COLOR_BORDER),
                        ("VALIGN", (0, 0), (-1, -1), "RIGHT"),
                        ("LEFTPADDING", (0, 0), (0, 0), self.config.PADDING_LOGO),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            self.config.PADDING_XXLARGE,
                        ),
                    ]
                )
            )
        else:
            # Fallback: apenas texto
            data = [[text]]
            table = Table(data, colWidths=[self.config.total_width])

            table.setStyle(
                TableStyle(
                    [
                        ("BORDER", (0, 0), (-1, -1), 1, self.config.COLOR_BORDER),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), self.config.PADDING_LOGO),
                        ("TOPPADDING", (0, 0), (-1, -1), self.config.PADDING_SMALL),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            self.config.PADDING_XXLARGE,
                        ),
                    ]
                )
            )

        return table

    def _get_logo_drawing(self) -> _DrawingFlowable | None:
        """Carrega logo SVG e converte para ReportLab Drawing."""
        try:
            # Determinar caminho do SVG
            if getattr(sys, "frozen", False):
                base_path = Path(
                    getattr(sys, "_MEIPASS", str(Path(__file__).parent.parent))
                )
                svg_path = base_path / "src" / "pdf" / "brasao_prefeitura.svg"
            else:
                svg_path = Path(__file__).parent / "brasao_prefeitura.svg"

            if not svg_path.exists():
                ErrorHandler.log(
                    f"Logo SVG não encontrado: {svg_path}",
                    level=ErrorLevel.WARNING,
                    context=ErrorContext.PDF_GENERATION,
                )
                return None

            # Converter SVG para ReportLab Drawing
            drawing = svg2rlg(str(svg_path))

            # Verificar se conversão foi bem-sucedida
            if drawing is None:
                ErrorHandler.log(
                    f"Falha ao converter SVG para Drawing: {svg_path}",
                    level=ErrorLevel.ERROR,
                    context=ErrorContext.PDF_GENERATION,
                )
                return None

            original_width = drawing.width
            original_height = drawing.height

            # Calcular fator de escala
            scale_factor = (
                self.config.LOGO_TARGET_SIZE / original_width
                if original_width > 0
                else 0.033
            )
            drawing.scale(scale_factor, scale_factor)
            drawing.width = original_width * scale_factor
            drawing.height = original_height * scale_factor
            drawing.hAlign = "LEFT"
            drawing.vAlign = "BOTTOM"

            ErrorHandler.log(
                f"Logo SVG carregado: {svg_path} (escala: {scale_factor:.3f})",
                level=ErrorLevel.INFO,
                context=ErrorContext.PDF_GENERATION,
            )

            return _DrawingFlowable(drawing, offset_y=self.config.LOGO_OFFSET_Y)

        except Exception as e:
            ErrorHandler.log(
                f"Erro ao carregar logo SVG: {e}",
                level=ErrorLevel.ERROR,
                context=ErrorContext.PDF_GENERATION,
            )
            return None


class PatientInfoTableBuilder:
    """Builder para tabela de informações do paciente"""

    def __init__(self, config: PDFConfig, styles: PDFStyleManager):
        self.config = config
        self.styles = styles

    def build(self, paciente: Dict, datas: Dict, avisos: Dict) -> List[Any]:
        """Cria tabela detalhada de informações do paciente"""
        # Preparar texto dos processos
        processos_list = paciente.get("processos", [])
        processos_lines = []
        for i, p in enumerate(processos_list):
            if i == 0:
                processos_lines.append(f"PROCESSO: Nº {p}")
            else:
                processos_lines.append(f"PROCESSO {i+1}: Nº {p}")
        processos_text = "<br/>".join([f"<b>{line}</b>" for line in processos_lines])

        # Cabeçalho dinâmico baseado no tipo
        header_text = (
            "RETIRADA DE INSULINA"
            if paciente.get("tipo") == "insulina"
            else "SESAP-10.2.0.2 – MANDADO JUDICIAL"
        )

        # Construir dados da tabela
        table_data = [
            # Linha 0: Título
            [
                Paragraph(
                    f"<b>{header_text}</b>",
                    self.styles.create_bold_centered_style(),
                )
            ],
            # Linha 1: Nome do paciente (3 cols) + Data (1 col, spans 3 rows)
            [
                Paragraph(
                    f'<b>PACIENTE: {paciente["nome"]}</b>',
                    self.styles.create_normal_style(),
                ),
                "",
                "",
                Paragraph(
                    f"<b>DATA DA RETIRADA:</b><br/><b>{datas['hoje']}</b>",
                    self.styles.create_bold_centered_style(),
                ),
            ],
        ]

        # Linha 2: Informações do processo (3 cols) + data continua
        if paciente.get("tipo") != "insulina":
            table_data.append(
                [
                    Paragraph(processos_text, self.styles.create_normal_style()),
                    "",
                    "",
                    "",
                ]
            )

        # Linha 3: Matrícula
        table_data.append(
            [
                Paragraph(
                    f'<b>MATRÍCULA: {paciente.get("matricula", "")}</b>',
                    self.styles.create_normal_style(),
                ),
                "",
                "",
                "",
            ]
        )

        # Linha 4: Próxima retirada
        table_data.append(
            [
                Paragraph(
                    f"<b>PRÓXIMA RETIRADA: {datas['proxima_vez']}</b>",
                    self.styles.create_header_style(13, leading=18),
                ),
                "",
                "",
                (
                    Paragraph(
                        "Atendimento <b>SOMENTE ATÉ<br/>3 DIAS ANTES</b> da data agendada.",
                        self.styles.create_centered_style(self.config.FONT_SIZE_SMALL),
                    )
                    if paciente.get("tipo") != "insulina"
                    else ""
                ),
            ]
        )

        current_row = 5

        # Adicionar tipo se existe
        if paciente.get("tipo"):
            tipo_text = paciente["tipo"].replace("_", " ").upper()
            table_data.append(
                [
                    Paragraph(
                        f"<b>{tipo_text}</b>", self.styles.create_bold_centered_style()
                    )
                ]
            )
            current_row += 1

            # Adicionar aviso DRS-IV se necessário
            if avisos.get("mostra_drs_iv"):
                table_data.append(
                    [
                        Paragraph(
                            "Caso a DRS-IV não tenha possibilidade de fornecimento, entrar em contato via telefone com o município para confirmação.",
                            self.styles.create_centered_style(int(9.6)),
                        )
                    ]
                )

        # Criar tabela unificada
        combined_table = Table(
            table_data,
            colWidths=[
                self.config.total_width * self.config.COL_PATIENT_LABEL,
                self.config.total_width * self.config.COL_PATIENT_NAME,
                self.config.total_width * self.config.COL_PATIENT_EMPTY,
                self.config.total_width * self.config.COL_PATIENT_DATE,
            ],
        )

        # Construir comandos de estilo
        style_commands = [
            ("GRID", (0, 0), (-1, -1), 1, self.config.COLOR_BORDER),
            # Linha de título
            ("BACKGROUND", (0, 0), (-1, 0), self.config.COLOR_HEADER_BG),
            ("SPAN", (0, 0), (-1, 0)),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            # Linhas de informações do paciente
            ("SPAN", (0, 1), (2, 1)),
        ]

        # DATA DA RETIRADA cell span - depende do tipo
        if paciente.get("tipo") == "insulina":
            # Spans 2 rows (1-2) quando processo está escondido
            style_commands.append(("SPAN", (3, 1), (3, 2)))
        else:
            # Spans 3 rows (1-3) quando processo é mostrado
            style_commands.append(("SPAN", (3, 1), (3, 3)))

        # Linhas de processo e matrícula - depende do tipo
        if paciente.get("tipo") != "insulina":
            # Com processo row
            style_commands.extend(
                [
                    ("SPAN", (0, 2), (2, 2)),  # Processo row
                    ("SPAN", (0, 3), (2, 3)),  # Matrícula row
                ]
            )
        else:
            # Sem processo row (matrícula sobe para linha 2)
            style_commands.extend(
                [
                    ("SPAN", (0, 2), (2, 2)),  # Matrícula row
                ]
            )

        # Estilização geral
        style_commands.extend(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, 0), self.config.PADDING_MEDIUM),
                ("BOTTOMPADDING", (0, 0), (-1, 0), self.config.PADDING_MEDIUM),
                ("TOPPADDING", (0, 1), (-1, -1), self.config.PADDING_LARGE),
                ("BOTTOMPADDING", (0, 1), (-1, -1), self.config.PADDING_LARGE),
                ("LEFTPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
            ]
        )

        # Linha de próxima retirada - depende do tipo
        if paciente.get("tipo") == "insulina":
            # Ocupa todas as 4 colunas quando aviso está escondido
            proxima_retirada_row = 3
            style_commands.extend(
                [
                    ("SPAN", (0, proxima_retirada_row), (3, proxima_retirada_row)),
                    (
                        "ALIGN",
                        (0, proxima_retirada_row),
                        (3, proxima_retirada_row),
                        "CENTER",
                    ),
                ]
            )
        else:
            # Comportamento original: col 0-2 + col 3 (aviso)
            proxima_retirada_row = 4
            style_commands.extend(
                [
                    ("SPAN", (0, proxima_retirada_row), (2, proxima_retirada_row)),
                    (
                        "ALIGN",
                        (0, proxima_retirada_row),
                        (2, proxima_retirada_row),
                        "CENTER",
                    ),
                    (
                        "ALIGN",
                        (3, proxima_retirada_row),
                        (3, proxima_retirada_row),
                        "CENTER",
                    ),
                ]
            )

        # Adicionar estilização para tipo e drs se existirem
        if paciente.get("tipo"):
            tipo_row = proxima_retirada_row + 1
            style_commands.extend(
                [
                    ("SPAN", (0, tipo_row), (-1, tipo_row)),
                    ("ALIGN", (0, tipo_row), (-1, tipo_row), "CENTER"),
                ]
            )

            if avisos.get("mostra_drs_iv"):
                drs_row = tipo_row + 1
                style_commands.extend(
                    [
                        ("SPAN", (0, drs_row), (-1, drs_row)),
                        ("ALIGN", (0, drs_row), (-1, drs_row), "CENTER"),
                        (
                            "TOPPADDING",
                            (0, drs_row),
                            (-1, drs_row),
                            self.config.PADDING_MEDIUM,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, drs_row),
                            (-1, drs_row),
                            self.config.PADDING_MEDIUM,
                        ),
                    ]
                )

        combined_table.setStyle(TableStyle(style_commands))

        return [combined_table]


class ItemsTableBuilder:
    """Builder para tabela de itens"""

    def __init__(self, config: PDFConfig, styles: PDFStyleManager):
        self.config = config
        self.styles = styles

    def build(self, itens: List[Dict]) -> Table:
        """Cria tabela de itens"""
        centered_small = self.styles.create_centered_style(self.config.FONT_SIZE_SMALL)
        centered_bold_small = self.styles.create_bold_small_style()

        # Linha de cabeçalho
        data = [
            [
                Paragraph("<b>ITEM</b>", centered_bold_small),
                Paragraph("<b>DESCRIÇÃO</b>", self.styles.create_bold_small_style()),
                Paragraph("<b>CÓDIGO</b>", centered_bold_small),
                Paragraph("<b>UNID.</b>", centered_bold_small),
                Paragraph("<b>QTDE.</b>", centered_bold_small),
                Paragraph("<b>DIAS</b>", centered_bold_small),
            ]
        ]

        # Linhas de dados
        for idx, item in enumerate(itens, start=1):
            data.append(
                [
                    Paragraph(f"{idx:02d}", centered_small),
                    Paragraph(item["descricao"], self.styles.create_normal_style()),
                    Paragraph(item["item_id"], centered_small),
                    Paragraph(item["unidade"], centered_small),
                    Paragraph(str(item["quantidade"]), centered_small),
                    Paragraph(str(item["dias"]), centered_small),
                ]
            )

        table = Table(
            data,
            colWidths=[
                self.config.total_width * self.config.COL_ITEM_NUM,
                self.config.total_width * self.config.COL_ITEM_DESC,
                self.config.total_width * self.config.COL_ITEM_CODE,
                self.config.total_width * self.config.COL_ITEM_UNIT,
                self.config.total_width * self.config.COL_ITEM_QTY,
                self.config.total_width * self.config.COL_ITEM_DAYS,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, self.config.COLOR_BORDER),
                    ("BACKGROUND", (0, 0), (-1, 0), self.config.COLOR_HEADER_BG),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (2, 0), (2, -1), "CENTER"),
                    ("ALIGN", (3, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), self.config.PADDING_MEDIUM),
                    ("LEFTPADDING", (0, 0), (-1, -1), self.config.PADDING_MEDIUM),
                    ("RIGHTPADDING", (0, 0), (-1, -1), self.config.PADDING_MEDIUM),
                ]
            )
        )

        return table


class PrescriptionTableBuilder:
    """Builder para tabela de datas de prescrição"""

    def __init__(self, config: PDFConfig, styles: PDFStyleManager):
        self.config = config
        self.styles = styles

    def build(self, datas: Dict) -> List[Any] | None:
        """Cria tabela com datas de prescrição. Retorna None se vazio."""
        ultima_receita = datas.get("ultima_receita", "-")
        validade_receita = datas.get("validade_receita", "-")

        # Retornar None se ambos estão vazios
        if ultima_receita in ("-", "", " ") and validade_receita in ("-", "", " "):
            return None

        # Usar valor se preenchido, senão "-"
        display_ultima = ultima_receita if ultima_receita not in ("-", "", " ") else "-"
        display_validade = (
            validade_receita if validade_receita not in ("-", "", " ") else "-"
        )

        data = [
            [
                Paragraph(
                    f"<b>TRAZER NOVA PRESCRIÇÃO APÓS: {display_validade}</b>",
                    self.styles.create_bold_centered_style(),
                ),
                Paragraph(
                    f"<b>ÚLTIMA PRESCRIÇÃO: {display_ultima}</b>",
                    self.styles.create_bold_centered_style(),
                ),
            ]
        ]

        table = Table(
            data,
            colWidths=[
                self.config.total_width * self.config.COL_PRESC_WIDE,
                self.config.total_width * self.config.COL_PRESC_NARROW,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, self.config.COLOR_BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                    ("LEFTPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                    ("RIGHTPADDING", (0, 0), (-1, -1), self.config.PADDING_MEDIUM),
                ]
            )
        )

        return [table]


class ProfessionalInfoTableBuilder:
    """Builder para tabela de informações do profissional"""

    def __init__(self, config: PDFConfig, styles: PDFStyleManager):
        self.config = config
        self.styles = styles

    def build(self, paciente: Dict) -> List[Any] | None:
        """Cria tabela com profissional e CRM. Retorna None se vazio."""
        prof = paciente.get("profissional", "")
        crm = paciente.get("crm", "")

        # Retornar None se ambos estão vazios
        if not prof and not crm:
            return None

        prof_display = prof or "—"
        crm_display = crm or "—"

        data = [
            [
                Paragraph(
                    f"<b>PROFISSIONAL: {prof_display}</b>",
                    self.styles.create_normal_style(),
                ),
                Paragraph(
                    f"<b>CRM: {crm_display}</b>", self.styles.create_normal_style()
                ),
            ]
        ]

        table = Table(
            data,
            colWidths=[
                self.config.total_width * self.config.COL_PRESC_WIDE,
                self.config.total_width * self.config.COL_PRESC_NARROW,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, self.config.COLOR_BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("TOPPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                    ("LEFTPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                    ("RIGHTPADDING", (0, 0), (-1, -1), self.config.PADDING_MEDIUM),
                ]
            )
        )

        return [table]


class AttentionBoxBuilder:
    """Builder para caixa de atenção"""

    def __init__(self, config: PDFConfig, styles: PDFStyleManager):
        self.config = config
        self.styles = styles

    def build(self, avisos: Dict, paciente: Dict | None = None) -> List[Any] | None:
        """Cria caixa de atenção/aviso. Retorna None para tipo insulina."""
        # Retornar None (ocultar box) se paciente for insulina
        if paciente and paciente.get("tipo") == "insulina":
            return None

        data = [
            [Paragraph("<b>ATENÇÃO!</b>", self.styles.create_bold_centered_style())],
            [
                Paragraph(
                    f"Trazer <b>prescrição médica atualizada {avisos['texto_validade']}.</b>",
                    self.styles.create_normal_style(),
                )
            ],
            [
                Paragraph(
                    "Itens fornecidos dentro do prazo de validade para período de consumo.",
                    self.styles.create_normal_style(),
                )
            ],
        ]

        table = Table(data, colWidths=[self.config.total_width])
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, self.config.COLOR_BORDER),
                    ("BACKGROUND", (0, 0), (0, 0), self.config.COLOR_HEADER_BG),
                    ("ALIGN", (0, 0), (0, 0), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), self.config.PADDING_MEDIUM),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), self.config.PADDING_MEDIUM),
                ]
            )
        )

        return [table]


class ObservationsBoxBuilder:
    """Builder para caixa de observações"""

    def __init__(self, config: PDFConfig, styles: PDFStyleManager):
        self.config = config
        self.styles = styles

    def build(self, observacoes: str) -> List[Any] | None:
        """Cria caixa de observações se texto existe. Retorna None se vazio."""
        if not observacoes or not observacoes.strip():
            return None

        data = [
            [Paragraph("<b>OBSERVAÇÕES:</b>", self.styles.create_normal_style())],
            [
                Paragraph(
                    observacoes.replace("\n", "<br/>"),
                    self.styles.create_bold_centered_style(),
                )
            ],
        ]

        table = Table(data, colWidths=[self.config.total_width])
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, self.config.COLOR_BORDER),
                    ("BACKGROUND", (0, 0), (0, 0), self.config.COLOR_HEADER_BG),
                    ("VALIGN", (0, 1), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        return [table]


class SignatureSectionBuilder:
    """Builder para seção de assinatura"""

    def __init__(self, config: PDFConfig, styles: PDFStyleManager):
        self.config = config
        self.styles = styles

    def build(self, atendido_por: str = "") -> List[Table]:
        """Cria seção 'atendido por' e assinaturas"""
        # Atendido por
        atendido_text = (
            f"<b>ATENDIDO POR:</b> {atendido_por}"
            if atendido_por
            else "<b>ATENDIDO POR:</b>"
        )
        atendido = Table(
            [[Paragraph(atendido_text, self.styles.create_bold_small_style())]],
            colWidths=[self.config.total_width],
        )
        atendido.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, self.config.COLOR_BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                    ("LEFTPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        # Seção de assinatura
        from reportlab.lib.styles import ParagraphStyle

        sig_data = [
            [
                Paragraph(
                    "<b>RESPONSÁVEL PELA RETIRADA</b>",
                    self.styles.create_bold_centered_style(),
                )
            ],
            [
                Paragraph(
                    "<b>IMPORTANTE: AO ASSINAR, DECLARO QUE RECEBI E CONFERI OS ITENS ACIMA DESCRITOS.</b>",
                    ParagraphStyle(
                        name="SigImportant",
                        parent=self.styles.create_bold_centered_style(),
                        fontSize=10,
                    ),
                )
            ],
            [Paragraph("NOME:", self.styles.create_normal_style())],
            [Paragraph("TEL:", self.styles.create_normal_style())],
        ]

        signature = Table(sig_data, colWidths=[self.config.total_width])
        signature.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, self.config.COLOR_BORDER),
                    ("BACKGROUND", (0, 0), (0, 0), self.config.COLOR_HEADER_BG),
                    ("ALIGN", (0, 0), (-1, 1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (0, 1), self.config.PADDING_LARGE),
                    ("BOTTOMPADDING", (0, 0), (0, 1), self.config.PADDING_MEDIUM),
                    ("TOPPADDING", (0, 2), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 2), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                ]
            )
        )

        return [atendido, signature]


class HoursSectionBuilder:
    """Builder para seção de horários de atendimento"""

    def __init__(self, config: PDFConfig, styles: PDFStyleManager):
        self.config = config
        self.styles = styles

    def build(self) -> Table:
        """Cria seção de horários de atendimento"""
        data = [
            [Paragraph("<b>ATENDIMENTO</b>", self.styles.create_bold_centered_style())],
            [
                Paragraph(
                    "<b>MANHÃ:</b> 09H – 11H", self.styles.create_bold_centered_style()
                ),
                Paragraph(
                    "<b>TARDE:</b> 14H – 16H", self.styles.create_bold_centered_style()
                ),
                Paragraph(
                    "<b>TELEFONE:</b> 3496-2400 (transferir para farmácia)",
                    self.styles.create_bold_centered_style(),
                ),
            ],
        ]

        table = Table(
            data,
            colWidths=[
                self.config.total_width * self.config.COL_HOURS_MORNING,
                self.config.total_width * self.config.COL_HOURS_AFTERNOON,
                self.config.total_width * self.config.COL_HOURS_PHONE,
            ],
        )

        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 1, self.config.COLOR_BORDER),
                    ("SPAN", (0, 0), (-1, 0)),
                    ("BACKGROUND", (0, 0), (-1, 0), self.config.COLOR_HEADER_BG),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), self.config.PADDING_LARGE),
                ]
            )
        )

        return table


# ============================================================================
# PDF GENERATOR CLASS
# ============================================================================


class MandadoJudicialPDF:
    """Gerador de PDF de Mandado Judicial - Refatorado"""

    def __init__(self, config: Optional[PDFConfig] = None):
        """
        Inicializa gerador de PDF.

        Args:
            config: Configurações PDF (opcional, usa padrão se não fornecido)
        """
        self.config = config or PDFConfig()
        self.styles = PDFStyleManager(self.config)
        self._init_builders()

    def _init_builders(self) -> None:
        """Inicializa todos os builders de tabela"""
        self.header_builder = HeaderTableBuilder(self.config, self.styles)
        self.patient_info_builder = PatientInfoTableBuilder(self.config, self.styles)
        self.items_builder = ItemsTableBuilder(self.config, self.styles)
        self.prescription_builder = PrescriptionTableBuilder(self.config, self.styles)
        self.professional_builder = ProfessionalInfoTableBuilder(
            self.config, self.styles
        )
        self.attention_builder = AttentionBoxBuilder(self.config, self.styles)
        self.observations_builder = ObservationsBoxBuilder(self.config, self.styles)
        self.signature_builder = SignatureSectionBuilder(self.config, self.styles)
        self.hours_builder = HoursSectionBuilder(self.config, self.styles)

    def generate(
        self, context: PDFDataContext, output_path: str | None = None
    ) -> BufferedWriter | BytesIO | None:
        """
        Gera PDF a partir do contexto de dados.

        **IMPORTANTE - Responsabilidade do Chamador:** Se output_path for fornecido, o chamador DEVE:
        1. Garantir que o diretório de saída existe e é gravável
        2. Sanitizar o nome do arquivo (use security.sanitize_filename)
        3. Validar o caminho para segurança (use security.validate_directory_path)

        O gerador de PDF NÃO validará caminhos - apenas cria o arquivo.

        Args:
            context: PDFDataContext object (deve ser criado via PDFDataContext.from_raw_data())
            output_path: Caminho do arquivo (opcional). Se None, retorna buffer BytesIO

        Returns:
            BytesIO buffer se output_path for None, caso contrário None

        Raises:
            IOError: Se arquivo não puder ser aberto para escrita
            ValueError: Se dados de contexto forem inválidos
        """
        try:
            # Criar buffer ou arquivo
            buffer: BufferedWriter | BytesIO
            if output_path:
                buffer = open(output_path, "wb")
            else:
                buffer = BytesIO()

            # Criar documento PDF
            doc = SimpleDocTemplate(
                buffer,
                pagesize=self.config.pagesize,
                leftMargin=self.config.margin,
                rightMargin=self.config.margin,
                topMargin=self.config.margin,
                bottomMargin=self.config.margin,
            )

            # Construir elementos
            elements: list[Any] = []

            # Cabeçalho
            elements.extend(
                (self.header_builder.build(), Spacer(1, self.config.SPACER_SMALL))
            )

            # Informações do paciente
            patient_elements = self.patient_info_builder.build(
                context.paciente, context.datas, context.avisos
            )
            elements.extend((*patient_elements, Spacer(1, self.config.SPACER_SMALL)))

            # Tabela de itens
            elements.append(self.items_builder.build(context.itens))

            # Datas de prescrição e informações profissionais (condicional)
            presc_dates_table = self.prescription_builder.build(context.datas)
            prof_table = self.professional_builder.build(context.paciente)

            if presc_dates_table or prof_table:
                elements.append(Spacer(1, self.config.SPACER_SMALL))
                if presc_dates_table:
                    elements.extend(presc_dates_table)
                if prof_table:
                    elements.extend(prof_table)
                elements.append(Spacer(1, self.config.SPACER_SMALL))
            else:
                elements.append(Spacer(1, self.config.SPACER_SMALL))

            # Caixa de atenção
            attention_elements = self.attention_builder.build(
                context.avisos, context.paciente
            )
            if attention_elements:
                elements.extend(attention_elements)
                elements.append(Spacer(1, self.config.SPACER_SMALL))
            else:
                elements.append(Spacer(1, self.config.SPACER_SMALL))

            # Observações
            obs_table = self.observations_builder.build(context.observacoes)
            if obs_table:
                elements.append(Spacer(1, self.config.SPACER_SMALL))
                elements.extend(obs_table)
                elements.append(Spacer(1, self.config.SPACER_SMALL))
            else:
                elements.append(Spacer(1, self.config.SPACER_SMALL))

            # Seções de assinatura
            sig_elements = self.signature_builder.build(context.atendido_por)
            elements.extend((*sig_elements, Spacer(1, self.config.SPACER_SMALL)))

            # Horários
            elements.append(self.hours_builder.build())

            # Construir PDF
            doc.build(elements)

            if output_path:
                buffer.close()
                ErrorHandler.log(
                    f"PDF gerado com sucesso: {output_path}",
                    level=ErrorLevel.INFO,
                    context=ErrorContext.PDF_GENERATION,
                )
                return None
            else:
                buffer.seek(0)
                ErrorHandler.log(
                    "PDF gerado com sucesso (buffer)",
                    level=ErrorLevel.INFO,
                    context=ErrorContext.PDF_GENERATION,
                )
                return buffer

        except ValueError as e:
            # Erro de validação de dados
            ErrorHandler.handle_error(
                e,
                context=ErrorContext.PDF_GENERATION,
                recovery_hint="Verifique se os dados são válidos",
                show_dialog=False,
            )
            return None
        except IOError as e:
            # Erro de I/O (arquivo não pode ser aberto/escrito)
            ErrorHandler.handle_error(
                e,
                context=ErrorContext.PDF_GENERATION,
                recovery_hint="Verifique permissões do diretório de saída",
                show_dialog=False,
            )
            return None
        except Exception as e:
            # Outros erros (ReportLab, SVG, etc)
            ErrorHandler.handle_error(
                e,
                context=ErrorContext.PDF_GENERATION,
                recovery_hint="Verifique se os dados são válidos",
                show_dialog=False,
            )
            return None


# ============================================================================
# WRAPPER PARA COMPATIBILIDADE (API PÚBLICA)
# ============================================================================


class ReportLabPDFGenerator:
    """
    Wrapper para compatibilidade com versão anterior.

    Mantém interface idêntica à versão legada para não quebrar código existente.
    """

    def __init__(self, _template_path: Any = None) -> None:
        """
        Inicializa gerador de PDF.

        Args:
            _template_path: Não usado na versão ReportLab (mantido para compatibilidade)
        """
        self.generator = MandadoJudicialPDF()

    def generate(self, context: dict, output_path: str) -> bool:
        """
        Gera PDF a partir do contexto de template.

        **IMPORTANTE - Responsabilidade do Chamador:** Antes de chamar este método, garanta:
        1. O diretório de saída existe e é gravável
        2. O nome do arquivo está sanitizado (use security.sanitize_filename)
        3. O caminho está validado para segurança (use security.validate_directory_path)

        O gerador de PDF NÃO validará caminhos - apenas cria o arquivo.

        Args:
            context: Dicionário com variáveis de template (paciente, itens, datas, etc.)
                     Deve ter os campos: patient_name, processos, itens, datas
            output_path: Caminho completo onde PDF deve ser salvo (deve ser pré-validado)

        Returns:
            bool: True se bem-sucedido, False se erro ocorreu
        """
        try:
            # Converter dict para PDFDataContext (única conversão)
            pdf_context = PDFDataContext.from_raw_data(context)

            # Gerar PDF usando PDFDataContext
            result = self.generator.generate(pdf_context, output_path)
            if (
                result is not None or output_path
            ):  # Sucesso se caminho fornecido ou buffer retornado
                return True
            return False
        except Exception as e:
            ErrorHandler.handle_error(
                e,
                context=ErrorContext.PDF_GENERATION,
                recovery_hint="Verifique se os dados são válidos",
                show_dialog=False,
            )
            return False
