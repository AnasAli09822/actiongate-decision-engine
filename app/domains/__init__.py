from app.schemas import Domain
from app.domains import ticket_triage, refund_approval, code_deploy

DOMAIN_MODULES = {
    Domain.TICKET_TRIAGE: ticket_triage,
    Domain.REFUND_APPROVAL: refund_approval,
    Domain.CODE_DEPLOY: code_deploy,
}
