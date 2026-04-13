"""Work item processing: ack → run skill → post reply."""

import re

from figwatch.domain import STATUS_PROCESSING, STATUS_REPLIED, STATUS_ERROR, load_trigger_config
from figwatch.providers.figma import figma_post, figma_delete

_EM_DASH = '\u2014'


def process_work_item(item, *, log=print, trigger_config=None):
    """Post ack, execute skill, post reply to Figma.

    Returns True on success, False on failure (error reply posted to Figma).
    """
    from figwatch.skills import execute_skill

    file_key = item.file_key
    pat = item.pat
    reply_to_id = item.reply_to_id
    trigger = item.trigger

    if item.on_status:
        item.on_status(STATUS_PROCESSING, item)

    ack_id = None
    try:
        ack = figma_post(f'/files/{file_key}/comments', {
            'message': f'\u23f3 {trigger.lstrip("@")} audit received \u2014 working on it\u2026',
            'comment_id': reply_to_id,
        }, pat)
        ack_id = ack.get('id')
        log(f'ack posted (comment {ack_id})')
    except Exception as e:
        log(f'ack failed (non-fatal): {e}')

    try:
        log(f'running skill {item.skill_path}\u2026')
        response = execute_skill(item)
        log(f'skill returned {len(response)} chars')

        if ack_id:
            try:
                figma_delete(f'/files/{file_key}/comments/{ack_id}', pat)
                log('ack deleted')
            except Exception as e:
                log(f'ack delete failed (non-fatal): {e}')

        # Strip trigger words from response to prevent feedback loops.
        for entry in (trigger_config or load_trigger_config()):
            trigger_word = entry.get('trigger', '')
            if trigger_word:
                response = re.sub(
                    r'(?<!\w)' + re.escape(trigger_word) + r'(?!\w)',
                    trigger_word.lstrip('@'),
                    response,
                    flags=re.IGNORECASE,
                )

        FIGMA_COMMENT_LIMIT = 4900
        if len(response) > FIGMA_COMMENT_LIMIT:
            total = len(response)
            truncated = response[:FIGMA_COMMENT_LIMIT - 60]
            last_nl = truncated.rfind('\n')
            if last_nl > FIGMA_COMMENT_LIMIT // 2:
                truncated = truncated[:last_nl]
            response = truncated + f'\n\n(truncated \u2014 full audit was {total} chars)'

        figma_post(f'/files/{file_key}/comments', {
            'message': response,
            'comment_id': reply_to_id,
        }, pat)
        log(f'reply posted to comment {reply_to_id}')

        if item.on_status:
            item.on_status(STATUS_REPLIED, item)
        return True

    except Exception as err:
        log(f'failed: {err}')
        if ack_id:
            try:
                figma_delete(f'/files/{file_key}/comments/{ack_id}', pat)
            except Exception:
                pass
        try:
            figma_post(f'/files/{file_key}/comments', {
                'message': f'Audit failed: {err}\n\n{_EM_DASH} FigWatch',
                'comment_id': reply_to_id,
            }, pat)
            log('error reply posted')
        except Exception:
            pass
        if item.on_status:
            item.on_status(STATUS_ERROR, item, error=str(err))
        return False
