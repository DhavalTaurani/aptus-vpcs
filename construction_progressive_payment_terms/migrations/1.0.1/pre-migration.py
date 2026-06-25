# -*- coding: utf-8 -*-

"""
Pre-migration script for construction progressive payment terms module
Fixes OWL template errors by ensuring proper field definitions
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Pre-migration script to prepare for OWL template fixes"""
    
    _logger.info("Starting pre-migration for construction_progressive_payment_terms v%s", version)
    
    # No specific database changes needed for this migration
    # The OWL template fixes are handled in the model/view updates
    
    _logger.info("Pre-migration completed successfully")