# checklist_questions.py

CHECKLIST_QUESTIONS = [
    {
        "category": "Información General",
        "questions": [
            {
                "key": "inf_gen_policy",
                "text": "¿Existe un responsable formal de la seguridad de la información en la organización?",
                "description": "Debe haber una persona o equipo designado para liderar y supervisar las políticas y controles de ciberseguridad."
            },
            {
                "key": "inf_gen_inventory",
                "text": "¿Se cuenta con un inventario actualizado de activos de información y hardware?",
                "description": "Un registro de todos los dispositivos, servidores y repositorios de datos críticos para la operación de la empresa."
            }
        ]
    },
    {
        "category": "Infraestructura",
        "questions": [
            {
                "key": "infra_rack",
                "text": "¿Los racks y servidores físicos están ubicados en un espacio seguro con control de acceso físico?",
                "description": "Evita manipulación física no autorizada, robos de discos o inserción de dispositivos USB maliciosos."
            },
            {
                "key": "infra_ups",
                "text": "¿Se cuenta con sistemas de energía ininterrumpida (UPS) operativos para servidores y red?",
                "description": "Protege los equipos contra cortes de energía y picos de tensión, y evita corrupción de datos."
            }
        ]
    },
    {
        "category": "Red",
        "questions": [
            {
                "key": "red_segmentation",
                "text": "¿La red de la empresa está segmentada (ej. VLAN para invitados, servidores y usuarios)?",
                "description": "Limita el movimiento lateral de un atacante o malware dentro de la red corporativa."
            },
            {
                "key": "red_dns",
                "text": "¿Se utilizan servidores DNS seguros o con filtrado de contenido para mitigar accesos a sitios maliciosos?",
                "description": "Servicios como Cloudflare (1.1.1.2) o Cisco Umbrella que bloquean la resolución de dominios maliciosos conocidos."
            }
        ]
    },
    {
        "category": "WiFi",
        "questions": [
            {
                "key": "wifi_encryption",
                "text": "¿Las redes WiFi corporativas utilizan cifrado robusto (WPA2-Enterprise o WPA3)?",
                "description": "Evita el uso de contraseñas débiles o compartidas para toda la oficina que puedan ser interceptadas."
            },
            {
                "key": "wifi_guest",
                "text": "¿Existe una red WiFi separada y aislada exclusivamente para invitados?",
                "description": "Los dispositivos ajenos a la empresa no deben tener visibilidad ni acceso a la red interna o servidores."
            }
        ]
    },
    {
        "category": "Servidores",
        "questions": [
            {
                "key": "serv_updates",
                "text": "¿Los servidores reciben parches de seguridad del sistema operativo mensualmente?",
                "description": "Las vulnerabilidades conocidas en sistemas operativos de servidores son el principal vector de ransomware."
            },
            {
                "key": "serv_encryption",
                "text": "¿Los servidores críticos tienen sus discos cifrados a nivel de hardware o sistema operativo?",
                "description": "Protege los datos confidenciales en caso de robo físico de los discos del servidor."
            }
        ]
    },
    {
        "category": "Backups",
        "questions": [
            {
                "key": "backup_frequency",
                "text": "¿Se realizan respaldos de seguridad (backups) diariamente de todos los datos críticos?",
                "description": "Asegura que la pérdida de datos máxima aceptable ante un desastre sea menor a 24 horas."
            },
            {
                "key": "backup_offline",
                "text": "¿Al menos una copia de los backups se almacena de forma offline o inmutable (fuera de la red local)?",
                "description": "Crucial para resistir ataques de ransomware, los cuales buscan y destruyen activamente los backups accesibles por red."
            },
            {
                "key": "backup_tests",
                "text": "¿Se realizan pruebas periódicas de restauración de copias de seguridad?",
                "description": "Un backup no verificado no es un backup confiable. Se recomienda realizar pruebas de restauración al menos semestralmente."
            }
        ]
    },
    {
        "category": "Correos",
        "questions": [
            {
                "key": "mail_spf",
                "text": "¿Están configurados correctamente los registros SPF, DKIM y DMARC en el dominio de correo?",
                "description": "Previene la suplantación de identidad (spoofing) de correos corporativos enviados en nombre de la empresa."
            },
            {
                "key": "mail_phishing",
                "text": "¿Se cuenta con filtrado antispam/antiphishing avanzado en la bandeja de entrada?",
                "description": "Protección para detectar y bloquear enlaces maliciosos o adjuntos peligrosos antes de que lleguen al usuario."
            }
        ]
    },
    {
        "category": "Microsoft 365 / Google Workspace",
        "questions": [
            {
                "key": "cloud_admin_mfa",
                "text": "¿Está habilitado el MFA de forma obligatoria para todos los administradores globales?",
                "description": "El compromiso de una cuenta de administrador de M365/Google Workspace otorga control total sobre la organización."
            },
            {
                "key": "cloud_logs",
                "text": "¿Está habilitada y configurada la retención de registros de auditoría de acceso y actividad?",
                "description": "Permite investigar incidentes, accesos desde ubicaciones anómalas o descargas masivas de información."
            }
        ]
    },
    {
        "category": "Accesos Remotos",
        "questions": [
            {
                "key": "remote_vpn",
                "text": "¿Los accesos remotos a la red interna se realizan exclusivamente a través de VPN segura con MFA?",
                "description": "Evita exponer servicios internos directamente a Internet sin capas previas de autenticación."
            },
            {
                "key": "remote_rdp",
                "text": "¿Se encuentra deshabilitado el acceso directo por RDP (puerto 3389) desde internet?",
                "description": "RDP expuesto directamente a internet es escaneado constantemente y vulnerado mediante fuerza bruta o exploits conocidos."
            }
        ]
    },
    {
        "category": "Endpoints",
        "questions": [
            {
                "key": "endpoint_privileges",
                "text": "¿Los usuarios operan en sus PCs/Notebooks sin privilegios de administrador local?",
                "description": "Mitiga drásticamente la instalación accidental de malware y programas no autorizados por parte de los usuarios."
            },
            {
                "key": "endpoint_updates",
                "text": "¿Se encuentra centralizada y automatizada la actualización de sistemas operativos en endpoints?",
                "description": "Políticas automáticas (ej. WSUS, Intune, actualizaciones automáticas en Windows) para parchar vulnerabilidades críticas."
            }
        ]
    },
    {
        "category": "Antivirus",
        "questions": [
            {
                "key": "av_active",
                "text": "¿Todas las computadoras y servidores tienen un software antivirus/EDR instalado y activo?",
                "description": "Debe haber una consola centralizada que alerte sobre dispositivos que no reportan estado de salud."
            },
            {
                "key": "av_updates",
                "text": "¿Las firmas y motores del antivirus se actualizan automáticamente todos los días?",
                "description": "Los endpoints deben actualizar firmas para detectar las últimas amenazas publicadas."
            }
        ]
    },
    {
        "category": "Firewall",
        "questions": [
            {
                "key": "fw_perimeter",
                "text": "¿Existe un firewall perimetral que controle el tráfico entrante y saliente a nivel de red?",
                "description": "Controla qué puertos y protocolos están permitidos hacia y desde internet."
            },
            {
                "key": "fw_rules",
                "text": "¿Se revisan periódicamente las reglas del firewall y se aplica el principio de menor privilegio?",
                "description": "Eliminar reglas obsoletas o excesivamente permisivas que dejen expuesta la red interna."
            }
        ]
    },
    {
        "category": "MFA",
        "questions": [
            {
                "key": "mfa_users",
                "text": "¿El uso de MFA es obligatorio para todos los usuarios en sus cuentas de correo corporativo?",
                "description": "El correo es la llave para restablecer contraseñas de otros servicios críticos de la empresa."
            },
            {
                "key": "mfa_vpn",
                "text": "¿Se exige MFA para la conexión VPN de los empleados?",
                "description": "Previene accesos no autorizados en caso de que las credenciales de la VPN sean filtradas o robadas."
            }
        ]
    },
    {
        "category": "Usuarios",
        "questions": [
            {
                "key": "user_onboarding",
                "text": "¿Existe un proceso formal de alta y baja de usuarios, asegurando la revocación inmediata al desvincular?",
                "description": "Evita cuentas 'huérfanas' activas pertenecientes a ex-empleados que puedan seguir accediendo."
            },
            {
                "key": "user_least_privilege",
                "text": "¿Se otorgan accesos y permisos basándose estrictamente en la necesidad de saber/operar?",
                "description": "Un usuario común no debe tener acceso de escritura en carpetas compartidas de contabilidad o recursos humanos."
            }
        ]
    },
    {
        "category": "Contraseñas",
        "questions": [
            {
                "key": "pass_complexity",
                "text": "¿Se exige longitud mínima de 12 caracteres y complejidad para contraseñas corporativas?",
                "description": "Evita contraseñas sencillas como 'Marzo2026' que son vulnerables a ataques de diccionario avanzados."
            },
            {
                "key": "pass_manager",
                "text": "¿Se fomenta o provee el uso de un gestor de contraseñas corporativo?",
                "description": "Ayuda a evitar la reutilización de contraseñas e impide que se escriban en post-its o archivos Excel sin cifrar."
            }
        ]
    },
    {
        "category": "Continuidad Operativa",
        "questions": [
            {
                "key": "cont_plan",
                "text": "¿Existe un plan de continuidad de negocio o recuperación ante desastres documentado?",
                "description": "Un plan sencillo paso a paso sobre cómo reanudar las operaciones críticas ante incidentes graves."
            },
            {
                "key": "cont_contacts",
                "text": "¿Se cuenta con una lista de contactos de emergencia de proveedores críticos actualizada?",
                "description": "Datos de ISP, soporte de servidores, telefonía y seguros cibernéticos accesibles fuera de la red local."
            }
        ]
    },
    {
        "category": "Políticas",
        "questions": [
            {
                "key": "policy_security",
                "text": "¿Existe una política de seguridad de la información aprobada por la dirección y comunicada al personal?",
                "description": "Sienta las bases legales y normativas sobre las expectativas de seguridad dentro del negocio."
            },
            {
                "key": "policy_device",
                "text": "¿Se cuenta con políticas de uso aceptable de dispositivos corporativos y BYOD?",
                "description": "Establece qué actividades se permiten en equipos de la empresa y cómo asegurar dispositivos personales."
            }
        ]
    },
    {
        "category": "Capacitación",
        "questions": [
            {
                "key": "training_phishing",
                "text": "¿Se realizan capacitaciones o simulacros de phishing periódicos para concientizar al personal?",
                "description": "El factor humano es el eslabón más explotado. La educación constante reduce la tasa de clicks en links maliciosos."
            }
        ]
    }
]

# Helper to find a question by key
def get_question_by_key(key):
    for cat in CHECKLIST_QUESTIONS:
        for q in cat["questions"]:
            if q["key"] == key:
                return q
    return None
