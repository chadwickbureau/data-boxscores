import marshmallow as marsh


class GameSourceSchema(marsh.Schema):
    """Schema for information on published source."""
    title = marsh.fields.Str()
    date = marsh.fields.Str()


class GameMetadataSchema(marsh.Schema):
    """Schema for source metadata for game."""
    source = marsh.fields.Nested(GameSourceSchema)


class GameSchema(marsh.Schema):
    """Schema for game information."""
    key = marsh.fields.Str()
    datetime = marsh.fields.Str()
    season = marsh.fields.Str()
    number = marsh.fields.Str()
    double_header = marsh.fields.Str()
    league = marsh.fields.Str()
    duration = marsh.fields.Str()


class PersonNameSchema(marsh.Schema):
    last = marsh.fields.Str()
    first = marsh.fields.Str()


class UmpireSchema(marsh.Schema):
    name = marsh.fields.Nested(PersonNameSchema)

    
class StatTotalsSchema(marsh.Schema):
    B_AB = marsh.fields.Str()
    B_R = marsh.fields.Str()
    B_H = marsh.fields.Str()
    F_PO = marsh.fields.Str()
    F_A = marsh.fields.Str()
    F_E = marsh.fields.Str()


class PlayerStatTotalsSchema(StatTotalsSchema):
    """Schema for player stat totals."""
    name = marsh.fields.Nested(PersonNameSchema)
    F_POS = marsh.fields.Str()
    substitution = marsh.fields.Str()
    
    
class PlayerSchema(marsh.Schema):
    """Schema for player entry on a team."""
    source = marsh.fields.Nested(PlayerStatTotalsSchema)


class TeamTotalsSchema(marsh.Schema):
    """Schema for team totals line."""
    source = marsh.fields.Nested(StatTotalsSchema)

    
class TeamSchema(marsh.Schema):
    """Schema for team information."""
    name = marsh.fields.Str()
    alignment = marsh.fields.Str()
    score = marsh.fields.Str()
    inning = marsh.fields.List(marsh.fields.Str())
    totals = marsh.fields.Nested(TeamTotalsSchema)
    player = marsh.fields.List(marsh.fields.Nested(PlayerSchema))


class CreditDetailSchema(marsh.Schema):
    """Schema for recording detail of statistical credits."""
    name = marsh.fields.Str()
    B_LOB = marsh.fields.Str()
    B_ROE = marsh.fields.Str()
    B_ER = marsh.fields.Str()
    B_2B = marsh.fields.Str()
    B_3B = marsh.fields.Str()
    B_HR = marsh.fields.Str()
    B_HP = marsh.fields.Str()
    B_SH = marsh.fields.Str()
    B_SF = marsh.fields.Str()
    B_SB = marsh.fields.Str()
    P_IP = marsh.fields.Str()
    P_H = marsh.fields.Str()
    P_BB = marsh.fields.Str()
    P_SO = marsh.fields.Str()
    P_HP = marsh.fields.Str()
    P_WP = marsh.fields.Str()
    F_PB = marsh.fields.Str()


class CreditSchema(marsh.Schema):
    """Schema for recording individual credit."""
    source = marsh.fields.Nested(CreditDetailSchema)
    infer = marsh.fields.Nested(CreditDetailSchema)


class CreditEventDetailSchema(marsh.Schema):
    """Schema for recording detail of event credit."""
    name = marsh.fields.List(marsh.fields.Str())
    F_DP = marsh.fields.Str()
    F_TP = marsh.fields.Str()

    
class CreditEventSchema(marsh.Schema):
    """Schema for recording event credit."""
    source = marsh.fields.Nested(CreditEventDetailSchema)
    infer = marsh.fields.Nested(CreditEventDetailSchema)

    
class CreditListSchema(marsh.Schema):
    """Schema for separately-quoted statistical credits."""
    team = marsh.fields.List(marsh.fields.Nested(CreditSchema))
    player = marsh.fields.List(marsh.fields.Nested(CreditSchema))
    event = marsh.fields.List(marsh.fields.Nested(CreditEventSchema))


class BoxscoreSchema(marsh.Schema):
    """Schema for a newspaper-boxscore data structure."""
    meta = marsh.fields.Nested(GameMetadataSchema)
    game = marsh.fields.Nested(GameSchema)
    umpire = marsh.fields.List(marsh.fields.Nested(UmpireSchema))
    team = marsh.fields.List(marsh.fields.Nested(TeamSchema))
    credit = marsh.fields.Nested(CreditListSchema)

