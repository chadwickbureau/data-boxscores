import datetime

import marshmallow as marsh


def validate_integer(n):
    try:
        if int(n) < 0:
            return False
    except ValueError:
        return False
    else:
        return True


def validate_IP(n):
    if "." not in n:
        return validate_integer(n)
    try:
        whole, frac = n.split(".")
    except ValueError:
        return False
    if frac not in ["0", "1", "2"]:
        return False
    if whole == "":
        return True
    return validate_integer(whole)


def validate_date(x):
    try:
        year, month, day = x.split("-")
    except ValueError:
        return False
    try:
        datetime.date(int(year), int(month), int(day))
    except ValueError:
        return False
    else:
        return True

def validate_position(x):
    if x == "":
        return False
    for pos in x.split("-"):
        if pos not in ["P", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF",
                       "PH", "PR"]:
            return False
    return True


def validate_duration(x):
    try:
        hours, minutes = x.split(":")
    except ValueError:
        return False
    try:
        if int(minutes) > 59 or int(minutes) < 0:
            return False
    except ValueError:
        return False
    return validate_integer(hours)


def validate_linescore(x):
    return x == "x" or validate_integer(x)


class GameSourceSchema(marsh.Schema):
    """Schema for information on published source."""
    title = marsh.fields.Str()
    date = marsh.fields.Str(validate=validate_date)


class GameMetadataSchema(marsh.Schema):
    """Schema for source metadata for game."""
    source = marsh.fields.Nested(GameSourceSchema)


class GameSchema(marsh.Schema):
    """Schema for game information."""
    key = marsh.fields.Str()
    datetime = marsh.fields.Str(validate=validate_date)
    season = marsh.fields.Str()
    number = marsh.fields.Str(
        validate=marsh.validate.OneOf(["1", "2"])
    )
    double_header = marsh.fields.Str(
        validate=marsh.validate.OneOf(["Y", "N"])
    )
    league = marsh.fields.Str()
    duration = marsh.fields.Str(validate=validate_duration)


class PersonNameSchema(marsh.Schema):
    last = marsh.fields.Str()
    first = marsh.fields.Str()


class UmpireSchema(marsh.Schema):
    name = marsh.fields.Nested(PersonNameSchema)

    
class StatTotalsSchema(marsh.Schema):
    B_AB = marsh.fields.Str(validate=validate_integer)
    B_R = marsh.fields.Str(validate=validate_integer)
    B_H = marsh.fields.Str(validate=validate_integer)
    F_PO = marsh.fields.Str(validate=validate_integer)
    F_A = marsh.fields.Str(validate=validate_integer)
    F_E = marsh.fields.Str(validate=validate_integer)


class PlayerStatTotalsSchema(StatTotalsSchema):
    """Schema for player stat totals."""
    name = marsh.fields.Nested(PersonNameSchema)
    F_POS = marsh.fields.Str(validate=validate_position)
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
    alignment = marsh.fields.Str(
        validate=marsh.validate.OneOf(["away", "home"])
    )
    score = marsh.fields.Str(validate=validate_integer)
    inning = marsh.fields.List(
        marsh.fields.Str(validate=validate_linescore))
    totals = marsh.fields.Nested(TeamTotalsSchema)
    player = marsh.fields.List(marsh.fields.Nested(PlayerSchema))


class CreditDetailSchema(marsh.Schema):
    """Schema for recording detail of statistical credits."""
    name = marsh.fields.Str()
    B_LOB = marsh.fields.Str(validate=validate_integer)
    B_ROE = marsh.fields.Str(validate=validate_integer)
    B_ER = marsh.fields.Str(validate=validate_integer)
    B_2B = marsh.fields.Str(validate=validate_integer)
    B_3B = marsh.fields.Str(validate=validate_integer)
    B_HR = marsh.fields.Str(validate=validate_integer)
    B_HP = marsh.fields.Str(validate=validate_integer)
    B_SH = marsh.fields.Str(validate=validate_integer)
    B_SF = marsh.fields.Str(validate=validate_integer)
    B_SB = marsh.fields.Str(validate=validate_integer)
    P_IP = marsh.fields.Str(validate=validate_IP)
    P_H = marsh.fields.Str(validate=validate_integer)
    P_BB = marsh.fields.Str(validate=validate_integer)
    P_SO = marsh.fields.Str(validate=validate_integer)
    P_HP = marsh.fields.Str(validate=validate_integer)
    P_WP = marsh.fields.Str(validate=validate_integer)
    F_PB = marsh.fields.Str(validate=validate_integer)


class CreditSchema(marsh.Schema):
    """Schema for recording individual credit."""
    source = marsh.fields.Nested(CreditDetailSchema)
    infer = marsh.fields.Nested(CreditDetailSchema)


class CreditEventDetailSchema(marsh.Schema):
    """Schema for recording detail of event credit."""
    name = marsh.fields.List(marsh.fields.Str())
    F_DP = marsh.fields.Str(validate=validate_integer)
    F_TP = marsh.fields.Str(validate=validate_integer)

    
class CreditEventSchema(marsh.Schema):
    """Schema for recording event credit."""
    source = marsh.fields.Nested(CreditEventDetailSchema)
    infer = marsh.fields.Nested(CreditEventDetailSchema)

    
class CreditListSchema(marsh.Schema):
    """Schema for separately-quoted statistical credits."""
    team = marsh.fields.List(marsh.fields.Nested(CreditSchema))
    player = marsh.fields.List(marsh.fields.Nested(CreditSchema))
    event = marsh.fields.List(marsh.fields.Nested(CreditEventSchema))


class GameOutcomeSchema(marsh.Schema):
    """Schema for game outcome information."""
    status = marsh.fields.Str(
        validate=marsh.validate.OneOf(["abandoned", "completed early",
                                       "final", "postponed"])
    )
    reason = marsh.fields.Str()

    
class BoxscoreSchema(marsh.Schema):
    """Schema for a newspaper-boxscore data structure."""
    meta = marsh.fields.Nested(GameMetadataSchema)
    game = marsh.fields.Nested(GameSchema)
    outcome = marsh.fields.Nested(GameOutcomeSchema)
    umpire = marsh.fields.List(marsh.fields.Nested(UmpireSchema))
    team = marsh.fields.List(marsh.fields.Nested(TeamSchema))
    credit = marsh.fields.Nested(CreditListSchema)

