"""Legal document views"""
import json
import os
from pathlib import Path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings


# Path to legal documents
LEGAL_DOCS_DIR = Path(settings.BASE_DIR) / 'legal_documents'
VERSIONS_FILE = LEGAL_DOCS_DIR / 'versions.json'


def load_versions():
    """Load versions.json file"""
    try:
        with open(VERSIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'terms': {'active_version': None, 'versions': []}, 'privacy': {'active_version': None, 'versions': []}}
    except Exception as e:
        print(f"Error loading versions.json: {e}")
        return {'terms': {'active_version': None, 'versions': []}, 'privacy': {'active_version': None, 'versions': []}}


def load_document_content(file_path):
    """Load markdown content from file"""
    try:
        full_path = LEGAL_DOCS_DIR / file_path
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error loading document {file_path}: {e}")
        return None


@api_view(['GET'])
@permission_classes([AllowAny])
def get_active_legal_document(request, document_type):
    """
    Get the currently active version of a legal document

    Args:
        document_type: 'terms' or 'privacy'

    Returns:
        200: Document found
        404: Document not found
    """
    if document_type not in ['terms', 'privacy']:
        return Response(
            {'error': 'Invalid document type. Must be "terms" or "privacy"'},
            status=status.HTTP_400_BAD_REQUEST
        )

    versions_data = load_versions()
    doc_type_data = versions_data.get(document_type, {})
    active_version = doc_type_data.get('active_version')

    if not active_version:
        return Response(
            {'error': f'No active {document_type} document found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Find the active version details
    version_info = None
    for v in doc_type_data.get('versions', []):
        if v['version'] == active_version:
            version_info = v
            break

    if not version_info:
        return Response(
            {'error': f'Active version {active_version} not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Load document content
    content = load_document_content(version_info['file'])
    if content is None:
        return Response(
            {'error': 'Document file not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    response_data = {
        'document_type': document_type,
        'version': version_info['version'],
        'title': version_info['title'],
        'content': content,
        'effective_date': version_info['effective_date'],
        'is_active': version_info.get('is_active', True)
    }

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_legal_document_version(request, document_type, version):
    """
    Get a specific version of a legal document

    Args:
        document_type: 'terms' or 'privacy'
        version: Version string

    Returns:
        200: Document found
        404: Document not found
    """
    if document_type not in ['terms', 'privacy']:
        return Response(
            {'error': 'Invalid document type. Must be "terms" or "privacy"'},
            status=status.HTTP_400_BAD_REQUEST
        )

    versions_data = load_versions()
    doc_type_data = versions_data.get(document_type, {})

    # Find the requested version
    version_info = None
    for v in doc_type_data.get('versions', []):
        if v['version'] == version:
            version_info = v
            break

    if not version_info:
        return Response(
            {'error': f'{document_type} document version {version} not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Load document content
    content = load_document_content(version_info['file'])
    if content is None:
        return Response(
            {'error': 'Document file not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    response_data = {
        'document_type': document_type,
        'version': version_info['version'],
        'title': version_info['title'],
        'content': content,
        'effective_date': version_info['effective_date'],
        'is_active': version_info.get('is_active', False)
    }

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def list_legal_document_versions(request, document_type):
    """
    List all versions of a legal document

    Args:
        document_type: 'terms' or 'privacy'

    Returns:
        200: List of document versions
    """
    if document_type not in ['terms', 'privacy']:
        return Response(
            {'error': 'Invalid document type. Must be "terms" or "privacy"'},
            status=status.HTTP_400_BAD_REQUEST
        )

    versions_data = load_versions()
    doc_type_data = versions_data.get(document_type, {})

    # Convert to response format (exclude content for list view)
    response_data = [
        {
            'version': v['version'],
            'title': v['title'],
            'effective_date': v['effective_date'],
            'is_active': v.get('is_active', False)
        }
        for v in doc_type_data.get('versions', [])
    ]

    return Response(response_data, status=status.HTTP_200_OK)




@api_view(['GET'])
@permission_classes([AllowAny])
def get_all_active_documents(request):
    """
    Get all currently active legal documents

    Returns:
        200: Dict with all active documents
    """
    versions_data = load_versions()
    response_data = {}

    for doc_type in ['terms', 'privacy']:
        doc_type_data = versions_data.get(doc_type, {})
        active_version = doc_type_data.get('active_version')

        if not active_version:
            continue

        # Find the active version details
        version_info = None
        for v in doc_type_data.get('versions', []):
            if v['version'] == active_version:
                version_info = v
                break

        if version_info:
            # Load document content
            content = load_document_content(version_info['file'])
            if content:
                response_data[doc_type] = {
                    'version': version_info['version'],
                    'title': version_info['title'],
                    'content': content,
                    'effective_date': version_info['effective_date']
                }

    return Response(response_data, status=status.HTTP_200_OK)
