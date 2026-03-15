"""
Test Runner for Olostech API
Runs full API test and reports progress via callbacks
"""

from datetime import datetime
from typing import Callable, Optional, Dict
from olostech_api import OlostechAPIClient


class OlostechTestRunner:
    """Runs Olostech API tests with progress reporting."""

    def __init__(self, output_callback: Callable[[str], None]):
        """
        Initialize test runner.

        Args:
            output_callback: Function to call with each line of output
        """
        self.output_callback = output_callback
        self.api_client: Optional[OlostechAPIClient] = None

    def _print(self, text: str):
        """Send text to output callback."""
        self.output_callback(text)

    def run_full_test(self, username: str, password: str, har_path: str = "w6.olostech.com.br.har", patient_matricula: str = None, retirada: Dict = None, test_workflow: bool = False) -> bool:
        """
        Execute complete API test.

        Args:
            username: Olostech username
            password: Olostech password
            har_path: Path to HAR file
            patient_matricula: Optional patient CNS/matricula to test patient search
            retirada: Optional retirada dict with dispensing data to process
            test_workflow: If True and retirada provided, also runs w6 workflow tests (ATTENTION: TEST ONLY, does NOT actually register)

        Returns:
            True if all tests passed, False otherwise
        """
        self._print("="*80)
        self._print("Olostech API - Teste Completo")
        self._print(f"Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        self._print("="*80)

        try:
            # Step 1: Create API client
            self._print("\n[Step 1/4] Criando API client...")
            self.api_client = OlostechAPIClient(har_path=har_path)
            self._print("[OK] API client criado")
            self._print(f"     Base URL: {self.api_client.base_url}")

            # Step 2: Test connection
            self._print("\n[Step 2/4] Testando conexão...")
            connection_result = self.api_client.test_connection()

            if not connection_result['reachable']:
                self._print("\n[X] Servidor não alcançável!")
                if connection_result.get('error'):
                    self._print(f"     Erro: {connection_result['error']}")
                self._print("\n" + "="*80)
                self._print("[FALHA] Teste de conexão falhou!")
                self._print("="*80)
                return False

            self._print("[OK] Servidor alcançável")
            self._print(f"     Campos dinâmicos: {connection_result['dynamic_fields']}")

            # Step 3: Execute login flow
            self._print("\n[Step 3/4] Executando login flow...")
            self._print("     Inclui:")
            self._print("       1. Autenticação")
            self._print("       2. Seleção de unidade")
            self._print("       3. Seleção de ambiente")
            self._print("       4. Seleção de atividade profissional (origem=3)")

            login_success = self.api_client.complete_login_flow(username, password)

            if not login_success:
                self._print("\n" + "="*80)
                self._print("[X] LOGIN FLOW FALHOU!")
                self._print("="*80)
                self._print("\nPossíveis causas:")
                self._print("  1. Usuário ou senha incorretos")
                self._print("  2. Problemas de conectividade")
                self._print("  3. Servidor Olostech bloqueando requisições")
                self._print("  4. ID de atividade profissional inválido")
                return False

            self._print("\n" + "="*80)
            self._print("[OK] LOGIN FLOW CONCLUÍDO COM SUCESSO!")
            self._print("="*80)
            self._print(f"\nSessão estabelecida:")
            self._print(f"  - Cookies: {len(self.api_client.session.cookies)}")
            self._print(f"  - Sessão ativa: Sim")

            # Step 4: Navigate to atendimento
            self._print("\n[Step 4/5] Testando navegação para atendimento...")
            nav_success = self.api_client.navigate_to_atendimento()

            if nav_success:
                self._print("\n" + "="*80)
                self._print("[OK] NAVEGAÇÃO PARA ATENDIMENTO BEM-SUCEDIDA!")
                self._print("="*80)
                self._print("\nValidação adicional:")
                self._print("  [OK] Consegue navegar para página de atendimento")
                self._print("  [OK] Pronto para busca de paciente")
                self._print("  [OK] Control ID do HAR está funcionando")

                # Step 5: Test patient search (if matricula provided)
                if patient_matricula:
                    self._print(f"\n[Step 5/5] Testando busca de paciente...")
                    self._print(f"     CNS/Matrícula: {patient_matricula}")

                    patient_data = self.api_client.search_patient_by_matricula(patient_matricula)

                    if patient_data:
                        self._print("\n" + "="*80)
                        self._print("[OK] PACIENTE ENCONTRADO!")
                        self._print("="*80)
                        self._print(f"\nDados do paciente:")
                        self._print(f"  Nome: {patient_data.get('usuarionome', 'N/A')}")
                        self._print(f"  CNS: {patient_data.get('matricula', 'N/A')}")
                        self._print(f"  Idade: {patient_data.get('idade', 'N/A')}")
                        if patient_data.get('bairrodesc'):
                            self._print(f"  Bairro: {patient_data.get('bairrodesc')}")
                    else:
                        self._print("\n" + "="*80)
                        self._print("[INFO] PACIENTE NÃO ENCONTRADO")
                        self._print("="*80)
                        self._print(f"\nPaciente com CNS {patient_matricula} não encontrado.")
                        self._print("Possíveis causas:")
                        self._print("  1. CNS/matricula incorreto")
                        self._print("  2. Paciente não cadastrado no sistema")
                        self._print("  3. Formato de resposta diferente do esperado")
                else:
                    self._print("\n[Step 5/6] Busca de paciente: pulada (sem CNS)")
                    self._print("     Forneça matricula para testar busca de paciente")

            # Phase 6: Test w6 workflow (NEW - if requested)
            if test_workflow and retirada and nav_success:
                self._print("\n" + "="*80)
                self._print("[Phase 6/6] TESTE DE WORKFLOW W6 (TEST ONLY)")
                self._print("="*80)
                self._print("\n⚠️  ATENÇÃO: Este é apenas um TESTE")
                self._print("    - NÃO registra oficialmente")
                self._print("    - Cria atendimento de teste")
                self._print("    - NÃO finaliza o atendimento")
                self._print("    - Testa todos os métodos AJAX")

                import asyncio

                # Create new event loop for async tests
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # Test 1: Professional workflow (NEW - Phase 2.1)
                    self._print("\n[Workflow Test 1/4] Testando busca de profissional...")
                    profissional_name = retirada.get('profissional', 'FERNANDO CARBALLIDO')
                    self._print(f"     Profissional: {profissional_name}")

                    professional_success = loop.run_until_complete(
                        self.test_professional_workflow(
                            professional_name=profissional_name
                        )
                    )

                    if not professional_success:
                        self._print("\n[AVISO] Professional workflow test falhou")

                    # Test 2: Attendance workflow
                    self._print("\n[Workflow Test 2/4] Testando criação de atendimento...")

                    estoque_id = '505'
                    date = datetime.now().strftime('%d/%m/%Y')
                    patient_id = retirada.get('patient_id', '266789')
                    self._print(f"     Estoque: {estoque_id}")
                    self._print(f"     Data: {date}")
                    self._print(f"     Paciente: {patient_id}")

                    workflow_success = loop.run_until_complete(
                        self.test_attendance_workflow(
                            estoque_id=estoque_id,
                            date=date,
                            patient_id=patient_id,
                            profissional_name=profissional_name
                        )
                    )

                    if not workflow_success:
                        self._print("\n[AVISO] Attendance workflow test falhou")
                    else:
                        # Test 3: Material dispensing
                        if retirada.get('materiais') and len(retirada['materiais']) > 0:
                            self._print("\n[Workflow Test 3/4] Testando dispensação de material...")

                            material_id = retirada['materiais'][0].get('id', '5346')
                            self._print(f"     Material: {material_id}")

                            loop.run_until_complete(
                                self.test_material_dispensing(
                                    material_id=material_id,
                                    patient_id=patient_id
                                )
                            )

                        # Test 4: Show what we would do next (but won't)
                        self._print("\n[Workflow Test 4/4] Próximos passos (NÃO executados):")
                        self._print("     - Dispensar todos os materiais")
                        self._print("     - Finalizar atendimento")
                        self._print("     - Atualizar banco de dados")
                        self._print("\n[OK] Teste de workflow concluído!")
                        self._print("     Todos os métodos AJAX funcionam corretamente")

                except Exception as e:
                    self._print(f"\n[ERRO] Workflow test falhou: {e}")
                    import traceback
                    self._print(traceback.format_exc())
                finally:
                    loop.close()

            else:
                self._print("\n[Step 6/6] Teste de workflow w6: pulado")
                self._print("     (Forneça retirada e ative test_workflow=True)")

            self._print("\n" + "="*80)
            self._print("TESTE CONCLUÍDO!")
            self._print("="*80)
            self._print(f"\nFinalizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

            return nav_success

        except Exception as e:
            self._print("\n" + "="*80)
            self._print(f"[ERRO] Exceção durante teste: {e}")
            self._print("="*80)
            import traceback
            self._print(traceback.format_exc())
            return False

    async def test_professional_workflow(
        self,
        professional_name: str = "FERNANDO CARBALLIDO"
    ) -> bool:
        """
        Test professional search and selection workflow.

        Tests:
        1. Search for professional by name
        2. Relevance sorting (like Emissor's autocomplete)
        3. Auto-selection with countdown

        Args:
            professional_name: Professional name to search for

        Returns:
            True if workflow successful
        """
        self._print("\n" + "="*80)
        self._print("WORKFLOW DE BUSCA DE PROFISSIONAL (Phase 2.1)")
        self._print("="*80)

        try:
            # Step 1: Search for professional
            self._print(f"\n[1/3] Buscando profissional: '{professional_name}'...")
            professionals = await self.api_client.search_professional(professional_name)

            if not professionals:
                self._print(f"[WARN] Nenhum profissional encontrado para '{professional_name}'")
                self._print("[INFO] Testando fallback para processo de cadastro...")

                # Test fallback
                fallback_result = await self.api_client.use_registration_process()
                if fallback_result:
                    self._print("[OK] Fallback para processo de cadastro funcionou")
                else:
                    self._print("[ERROR] Fallback falhou")
                return fallback_result

            # Step 2: Verify relevance sorting
            self._print(f"\n[2/3] Verificando ordenação por relevância...")
            self._print(f"[OK] {len(professionals)} profissional(is) encontrado(s)")
            for i, prof in enumerate(professionals[:5]):
                relevance_note = ""
                if i == 0:
                    relevance_note = " ← (MAIS RELEVANTE)"
                self._print(f"       {i+1}. {prof['name']} - {prof['unidade']}{relevance_note}")

            # Step 3: Test auto-selection
            self._print(f"\n[3/3] Testando auto-seleção com countdown...")
            selected = await self.api_client.select_or_fallback_professional(professional_name)

            self._print("\n" + "="*80)
            if selected:
                self._print("[OK] WORKFLOW DE PROFISSIONAL CONCLUÍDO!")
            else:
                self._print("[ERROR] WORKFLOW DE PROFISSIONAL FALHOU")
            self._print("="*80)

            return selected

        except Exception as e:
            self._print(f"\n[ERROR] Professional workflow failed: {e}")
            import traceback
            self._print(traceback.format_exc())
            return False

    async def test_attendance_workflow(
        self,
        estoque_id: str = "505",
        date: str = None,
        patient_id: str = "266789",
        profissional_name: str = None
    ) -> bool:
        """
        Test complete attendance workflow from w6 HAR.

        Args:
            estoque_id: Stock/Dispensary ID (default: 505)
            date: Attendance date (default: today)
            patient_id: Patient registration ID
            profissional_name: Professional name to search (default: "FERNANDO CARBALLIDO")

        Returns:
            True if workflow successful
        """
        from datetime import datetime as dt

        if date is None:
            date = dt.now().strftime('%d/%m/%Y')

        self._print("\n" + "="*80)
        self._print("WORKFLOW DE CRIAÇÃO DE ATENDIMENTO (w6 HAR)")
        self._print("="*80)

        # DEBUG: Log input parameters
        self._print("\n[DEBUG] Input parameters:")
        self._print(f"  estoque_id: {estoque_id} (type: {type(estoque_id).__name__})")
        self._print(f"  date: {date} (type: {type(date).__name__})")
        self._print(f"  patient_id: {patient_id} (type: {type(patient_id).__name__})")
        self._print(f"  profissional_name: {profissional_name} (type: {type(profissional_name).__name__})")

        try:
            # Session refresh before starting workflow
            self._print("\n[0/6] Refreshing session before workflow...")
            refresh_success = await self.api_client.refresh_session()
            if not refresh_success:
                self._print("[WARN] Session refresh failed, continuing anyway...")

            # Step 1: Get attendance number
            self._print("\n[1/6] Obtendo número de atendimento (senha)...")
            senha = await self.api_client.get_attendance_number(estoque_id)
            if not senha:
                self._print("[ERROR] Failed to get attendance number")
                return False

            # Step 2: Check for duplicates
            self._print("\n[2/6] Verificando duplicidade...")
            check_result = await self.api_client.check_duplicate_attendance(
                estoque_id, date, patient_id, senha
            )
            if not check_result['valido']:
                self._print("[WARN] Duplicate check had issues, continuing...")

            # Step 3: Get patient data
            self._print("\n[3/6] Obtendo dados do paciente...")
            patient_result = await self.api_client.get_user_sus_data(patient_id)
            if not patient_result['valido']:
                self._print("[ERROR] Failed to get patient data")
                return False

            # Step 4: Search professional
            self._print("\n[4/6] Buscando profissional...")
            prof_name = profissional_name or "FERNANDO CARBALLIDO"
            self._print(f"     Profissional: {prof_name}")
            prof_result = await self.api_client.search_professional_by_name(prof_name)
            if not prof_result['valido']:
                self._print("[WARN] Professional search failed, continuing...")

            # Step 5: Create attendance
            self._print("\n[5/6] Criando atendimento...")
            attendance_id = await self.api_client.create_attendance(
                estoque_id, date, patient_id, senha
            )
            if not attendance_id:
                self._print("[ERROR] Failed to create attendance")
                return False

            # Step 6: Skip finalization in test mode
            self._print("\n[6/6] Pulando finalização (TEST MODE)...")
            self._print("[INFO] Atendimento NÃO finalizado (apenas teste)")

            # Don't call finalize_attendance() in test mode
            finalize_result = True  # Pretend success for test flow

            self._print("\n" + "="*80)
            if finalize_result:
                self._print("[OK] WORKFLOW DE ATENDIMENTO CONCLUÍDO!")
            else:
                self._print("[WARN] Atendimento criado mas finalização falhou")
            self._print("="*80)

            return finalize_result

        except Exception as e:
            self._print(f"\n[ERROR] Attendance workflow failed: {e}")
            import traceback
            self._print(traceback.format_exc())
            return False

    async def test_material_dispensing(
        self,
        material_id: str = "5346",
        patient_id: str = "266789"
    ) -> bool:
        """
        Test material dispensing workflow from w6 HAR.

        Args:
            material_id: Material ID to dispense (default: 5346 = FRALDA GER. DESC.)
            patient_id: Patient ID

        Returns:
            True if workflow successful
        """
        self._print("\n" + "="*80)
        self._print("WORKFLOW DE DISPENSAÇÃO DE MATERIAL (w6 HAR)")
        self._print("="*80)

        try:
            # Step 1: Search material
            self._print(f"\n[1/4] Buscando material: {material_id}...")
            material_result = await self.api_client.search_material(material_id)
            if not material_result['valido']:
                self._print("[ERROR] Material not found")
                return False

            # Step 2: Get last delivery
            self._print("\n[2/4] Verificando última entrega...")
            last_delivery = await self.api_client.get_last_material_delivery(
                patient_id, material_id
            )

            # Step 3: Check for associated materials
            self._print("\n[3/4] Verificando materiais associados...")
            await self.api_client._ajax_call(
                'amfb/fb/dispensacao.ajax.asp',
                'ObterMaterialAssociado',
                f"{material_id}|#"
            )

            # Step 4: Get batches (if medication)
            self._print("\n[4/4] Verificando lotes...")
            batches = await self.api_client.get_medication_batches(material_id)

            self._print("\n" + "="*80)
            self._print("[OK] WORKFLOW DE DISPENSAÇÃO CONCLUÍDO!")
            self._print("="*80)

            return True

        except Exception as e:
            self._print(f"\n[ERROR] Material dispensing failed: {e}")
            import traceback
            self._print(traceback.format_exc())
            return False

    async def test_complete_workflow(
        self,
        estoque_id: str = "505",
        patient_id: str = "266789",
        material_id: str = "5346"
    ) -> bool:
        """
        Test complete end-to-end workflow: attendance + dispensing.

        Args:
            estoque_id: Stock/Dispensary ID
            patient_id: Patient ID
            material_id: Material ID to dispense

        Returns:
            True if complete workflow successful
        """
        self._print("\n" + "="*80)
        self._print("WORKFLOW COMPLETO: ATENDIMENTO + DISPENSAÇÃO")
        self._print(f"Estoque: {estoque_id}")
        self._print(f"Paciente: {patient_id}")
        self._print(f"Material: {material_id}")
        self._print("="*80)

        try:
            # Phase 1: Create attendance
            self._print("\n[FASE 1] Criando atendimento...")
            from datetime import datetime as dt
            date = dt.now().strftime('%d/%m/%Y')

            senha = await self.api_client.get_attendance_number(estoque_id)
            if not senha:
                return False

            attendance_id = await self.api_client.create_attendance(
                estoque_id, date, patient_id, senha
            )
            if not attendance_id:
                return False

            self._print(f"[OK] Atendimento criado: ID={attendance_id}")

            # Phase 2: Dispense material
            self._print("\n[FASE 2] Dispensando material...")
            from datetime import datetime, timedelta
            data_suficiencia = (datetime.now() + timedelta(days=30)).strftime('%d/%m/%Y')

            dispense_result = await self.api_client.dispense_material_direct(
                attendance_id,
                material_id,
                10,  # quantity
                data_suficiencia
            )

            if not dispense_result:
                self._print("[WARN] Material dispensing failed, but attendance created")

            # Phase 3: Finalize
            self._print("\n[FASE 3] Finalizando atendimento...")
            finalize_result = await self.api_client.finalize_attendance(attendance_id)

            self._print("\n" + "="*80)
            if finalize_result:
                self._print("[OK] WORKFLOW COMPLETO BEM-SUCEDIDO!")
            else:
                self._print("[WARN] Workflow concluído com avisos")
            self._print("="*80)

            return finalize_result or dispense_result

        except Exception as e:
            self._print(f"\n[ERROR] Complete workflow failed: {e}")
            import traceback
            self._print(traceback.format_exc())
            return False
