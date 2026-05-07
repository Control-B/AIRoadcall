"""fleet_and_org_models

Revision ID: a1b2c3d4e5f6
Revises: 69e9a459
Create Date: 2025-01-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a1b2c3d4e5f6'
down_revision = '69e9a459'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # vertical_type enum
    vertical_type_enum = sa.Enum('shops', 'fleet', name='vertical_type_enum')
    vertical_type_enum.create(op.get_bind())

    # organizations
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('vertical_type', sa.Enum('shops', 'fleet', name='vertical_type_enum', create_constraint=True), nullable=False),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(30), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])

    # fleet_profiles
    op.create_table(
        'fleet_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dot_number', sa.String(20), nullable=True),
        sa.Column('mc_number', sa.String(20), nullable=True),
        sa.Column('fleet_size', sa.Integer(), nullable=True),
        sa.Column('primary_lanes', sa.Text(), nullable=True),
        sa.Column('preferred_vendor_radius_miles', sa.Integer(), nullable=True, server_default='100'),
        sa.Column('emergency_contact_name', sa.String(255), nullable=True),
        sa.Column('emergency_contact_phone', sa.String(30), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_fleet_profiles_organization_id', 'fleet_profiles', ['organization_id'])

    # vehicles
    op.create_table(
        'vehicles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('unit_number', sa.String(50), nullable=False),
        sa.Column('vin', sa.String(20), nullable=True),
        sa.Column('year', sa.String(4), nullable=True),
        sa.Column('make', sa.String(100), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('vehicle_type', sa.String(50), nullable=True),
        sa.Column('license_plate', sa.String(20), nullable=True),
        sa.Column('license_state', sa.String(10), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_vehicles_organization_id', 'vehicles', ['organization_id'])

    # drivers
    op.create_table(
        'drivers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('phone', sa.String(30), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('cdl_number', sa.String(50), nullable=True),
        sa.Column('cdl_state', sa.String(10), nullable=True),
        sa.Column('assigned_vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_drivers_organization_id', 'drivers', ['organization_id'])

    # vendors
    op.create_table(
        'vendors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(30), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(120), nullable=True),
        sa.Column('state', sa.String(10), nullable=True),
        sa.Column('zip_code', sa.String(10), nullable=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('service_types', sa.Text(), nullable=True),
        sa.Column('heavy_duty_capable', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('service_radius_miles', sa.Integer(), nullable=True),
        sa.Column('operates_24_7', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('average_rating', sa.Float(), nullable=True),
        sa.Column('total_jobs_completed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_vendors_state', 'vendors', ['state'])

    # incident_status enum
    incident_status_enum = sa.Enum('open', 'dispatched', 'en_route', 'on_site', 'resolved', 'cancelled', name='incident_status_enum')
    incident_status_enum.create(op.get_bind())

    # roadside_incidents
    op.create_table(
        'roadside_incidents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('public_incident_id', sa.String(20), nullable=False, unique=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('drivers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('caller_name', sa.String(255), nullable=True),
        sa.Column('caller_phone', sa.String(30), nullable=False),
        sa.Column('issue_description', sa.Text(), nullable=True),
        sa.Column('vehicle_description', sa.String(255), nullable=True),
        sa.Column('breakdown_lat', sa.Float(), nullable=True),
        sa.Column('breakdown_lng', sa.Float(), nullable=True),
        sa.Column('breakdown_city', sa.String(120), nullable=True),
        sa.Column('breakdown_state', sa.String(10), nullable=True),
        sa.Column('breakdown_address', sa.Text(), nullable=True),
        sa.Column('location_captured_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assigned_vendor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vendors.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.Enum('open', 'dispatched', 'en_route', 'on_site', 'resolved', 'cancelled', name='incident_status_enum', create_constraint=True), nullable=False, server_default='open'),
        sa.Column('retell_call_id', sa.String(255), nullable=True),
        sa.Column('call_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_roadside_incidents_public_incident_id', 'roadside_incidents', ['public_incident_id'])
    op.create_index('ix_roadside_incidents_organization_id', 'roadside_incidents', ['organization_id'])

    # location_session_status enum
    loc_status_enum = sa.Enum('pending', 'link_sent', 'captured', 'expired', name='location_session_status_enum')
    loc_status_enum.create(op.get_bind())

    # location_capture_sessions
    op.create_table(
        'location_capture_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roadside_incidents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('token', sa.String(128), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.Enum('pending', 'link_sent', 'captured', 'expired', name='location_session_status_enum', create_constraint=True), nullable=False, server_default='pending'),
        sa.Column('sms_sent_to', sa.String(30), nullable=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('accuracy_meters', sa.Float(), nullable=True),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_location_capture_sessions_token', 'location_capture_sessions', ['token'])

    # integration_provider enum
    integration_provider_enum = sa.Enum('ghl', 'twilio', 'stripe', 'retell', 'telnyx', 'samsara', 'motive', name='integration_provider_enum')
    integration_provider_enum.create(op.get_bind())

    # integration_connections
    op.create_table(
        'integration_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.Enum('ghl', 'twilio', 'stripe', 'retell', 'telnyx', 'samsara', 'motive', name='integration_provider_enum', create_constraint=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('external_account_id', sa.String(255), nullable=True),
        sa.Column('credentials_json', sa.Text(), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.Column('webhook_url', sa.String(500), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_integration_connections_organization_id', 'integration_connections', ['organization_id'])


def downgrade() -> None:
    op.drop_table('integration_connections')
    op.drop_table('location_capture_sessions')
    op.drop_table('roadside_incidents')
    op.drop_table('vendors')
    op.drop_table('drivers')
    op.drop_table('vehicles')
    op.drop_table('fleet_profiles')
    op.drop_table('organizations')

    op.execute("DROP TYPE IF EXISTS integration_provider_enum")
    op.execute("DROP TYPE IF EXISTS location_session_status_enum")
    op.execute("DROP TYPE IF EXISTS incident_status_enum")
    op.execute("DROP TYPE IF EXISTS vertical_type_enum")
