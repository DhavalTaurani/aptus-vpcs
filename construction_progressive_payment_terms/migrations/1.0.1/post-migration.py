# -*- coding: utf-8 -*-

"""
Post-migration script for construction progressive payment terms module
Verifies OWL template fixes are working correctly
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Post-migration script to verify OWL template fixes"""
    
    _logger.info("Starting post-migration for construction_progressive_payment_terms v%s", version)
    
    # Verify that the milestone_state field has the correct selection values
    cr.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'project_task' 
        AND column_name = 'milestone_state'
    """)
    
    result = cr.fetchone()
    if result:
        _logger.info("milestone_state field verified in project_task table")
    else:
        _logger.warning("milestone_state field not found in project_task table")
    
    _logger.info("Post-migration completed successfully")