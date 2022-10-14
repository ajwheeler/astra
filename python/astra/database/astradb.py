import datetime
import json
import os
import hashlib
from functools import lru_cache, cached_property
from sdss_access import SDSSPath
from peewee import (
    IntegrityError,
    fn,
    SqliteDatabase,
    BooleanField,
    IntegerField,
    AutoField,
    TextField,
    ForeignKeyField,
    DateTimeField,
    BigIntegerField,
    FloatField,
    BooleanField,
)
from sdssdb.connection import DatabaseConnection, PeeweeDatabaseConnection
from sdssdb.peewee import BaseModel
from astra import config, log
from astra.utils import flatten
from astra import __version__
from tqdm import tqdm
from time import sleep

# Environment variable overrides all, for running CI tests.
_database_url = os.environ.get("ASTRA_DATABASE_URL", None)
if _database_url is not None:
    from playhouse.sqlite_ext import (
        SqliteExtDatabase as AstraDatabaseConnection,
        JSONField,
    )

    log.info(
        f"Using ASTRA_DATABASE_URL enironment variable, and assuming a SQLite database"
    )

    # The PeeweeDatabaseConnection assumes a postgresql database under the hood. Argh!
    database = AstraDatabaseConnection(_database_url, thread_safe=True)
    schema = None

else:
    # The documentation says we should be using the PostgresqlExtDatabase if we are using a
    # BinaryJSONField, but that class is incompatible with PeeweeDatabaseConnection, and it
    # doesn't look like we need anything different from the existing PostgresqlDatabase class.
    from playhouse.postgres_ext import BinaryJSONField as JSONField
    from playhouse.postgres_ext import ArrayField

    _database_config = config.get("astra_database", {})

    class AstraDatabaseConnection(PeeweeDatabaseConnection):
        dbname = _database_config.get("dbname", None)

    database = AstraDatabaseConnection(autoconnect=True)
    schema = _database_config.get("schema", None)

    profile = _database_config.get("profile", None)
    if profile is not None:
        try:
            database.set_profile(profile)
        except AssertionError as e:
            log.exception(e)
            log.warning(
                f"""
            Database profile '{profile}' set in Astra configuration file, but there is no database
            profile called '{profile}' found in ~/.config/sdssdb/sdssdb.yml -- it should look like:

            {profile}:
                user: [USER]
                host: [HOST]
                port: 5432
                domain: [DOMAIN]
            See https://sdssdb.readthedocs.io/en/stable/intro.html#supported-profiles for more details.
            If the profile name '{profile}' is incorrect, you can change the 'database' / 'profile' key
            in ~/.astra/astra.yml
            """
            )


class AstraBaseModel(BaseModel):
    class Meta:
        database = database
        schema = schema


_sdss_path_instances = {}


class Source(AstraBaseModel):

    catalogid = BigIntegerField(primary_key=True)

    @property
    def data_products(self):
        return (
            DataProduct.select()
            .join(SourceDataProduct)
            .join(Source)
            .where(Source.catalogid == self.catalogid)
        )

    '''
    # Sould link source and data product/task to the OUTPUT table... then it'd be easier.
    @property
    def outputs(self):
        outputs = []
        o = TaskOutput.get(TaskOutput.task == self)
        for expr, column in o.output.dependencies():
            if column.model not in (TaskOutput, AstraOutputBaseModel):
                outputs.extend(column.model.select().where(column.model.task == self))
        return sorted(outputs, key=lambda x: x.output_id)
    '''

class DataProductKeywordsField(JSONField):
    def adapt(self, kwargs):
        # See https://github.com/sdss/astra/issues/8
        coerced = {}
        coerce_types = {
            # apVisit
            "mjd": int,
            # Some APOGEE paths were periodically screwed up in the database.
            "field": lambda _: str(_).strip(),
            "fiber": int,
            "apred": str,
            "healpix": int,
            # specFull
            "fieldid": int,
        }
        for key, value in kwargs.items():
            key = key.strip().lower()
            if key in coerce_types:
                value = coerce_types[key](value)
            coerced[key] = value
        return coerced


_template_dpkwf = DataProductKeywordsField()


class DataProduct(AstraBaseModel):

    id = AutoField()

    release = TextField(null=True)
    filetype = TextField()
    kwargs = DataProductKeywordsField()
    kwargs_hash = TextField()

    metadata = JSONField(null=True)

    created = DateTimeField(default=datetime.datetime.now)
    updated = DateTimeField(default=datetime.datetime.now)

    class Meta:
        indexes = (
            # Always remember to put the comma at the end.
            (("release", "filetype", "kwargs_hash"), True),
        )

    def __init__(self, *args, **kwargs):
        # Adapt keywords
        adapted, hashed = self.adapt_and_hash_kwargs(kwargs.get("kwargs", {}))
        kwargs["kwargs"] = adapted
        kwargs.setdefault("kwargs_hash", hashed)
        super(DataProduct, self).__init__(*args, **kwargs)


    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.filetype}): id={self.id}>"


    @classmethod
    def adapt_and_hash_kwargs(cls, kwargs):
        adapted = _template_dpkwf.adapt(kwargs)
        hashed = hashlib.md5(json.dumps(adapted).encode("utf-8")).hexdigest()
        return (adapted, hashed)

    # Don't do filtering just based on .get(), because sometimes we might be querying by partial keywords
    # and we'll be searching with an incomplete (and incorrect) hash.

    @classmethod
    def get_or_create(cls, **kwargs):
        defaults = kwargs.pop("defaults", {})
        query = cls.select()

        for field, value in kwargs.items():
            # Just search by kwargs hash
            if field == "kwargs":
                # instead, seach by kwargs hash
                adapted, hashed = cls.adapt_and_hash_kwargs(value)
                query = query.where(getattr(cls, "kwargs_hash") == hashed)
            else:
                query = query.where(getattr(cls, field) == value)

        try:
            return query.get(), False
        except cls.DoesNotExist:
            try:
                if defaults:
                    kwargs.update(defaults)
                with cls._meta.database.atomic():
                    return cls.create(**kwargs), True
            except IntegrityError as exc:
                try:
                    return query.get(), False
                except cls.DoesNotExist:
                    raise exc

    @property
    def input_to_tasks(self):
        return (
            Task.select()
            .join(TaskInputDataProducts)
            .join(DataProduct)
            .where(DataProduct.id == self.id)
        )

    @cached_property
    def path(self):
        '''
        if self.filetype in ("mwmStar", "mwmVisit"):
            catalogid = self.kwargs['cat_id']
            k = 100
            #catalogid_groups = f"{(catalogid // k) % k:.0f}/{catalogid % k:.0f}"
            catalogid_groups = f"{(catalogid // k) % k:0>2.0f}/{catalogid % k:0>2.0f}"

            log.warn("hard-coding in path")
            from astra.utils import expand_path
            
            if self.filetype == "mwmStar":
                return expand_path("$MWM_ASTRA/{v_astra}/{run2d}-{apred}/spectra/star/{catalogid_groups}/mwmStar-{v_astra}-{cat_id}.fits".format(catalogid_groups=catalogid_groups, **self.kwargs))
            else:
                return expand_path("$MWM_ASTRA/{v_astra}/{run2d}-{apred}/spectra/visit/{catalogid_groups}/mwmVisit-{v_astra}-{cat_id}.fits".format(catalogid_groups=catalogid_groups, **self.kwargs))

        elif self.filetype.startswith("astraStar"):
            pipeline = self.filetype[len("astraStar"):]
            catalogid = self.kwargs['cat_id']
            k = 100
            #catalogid_groups = f"{(catalogid // k) % k:.0f}/{catalogid % k:.0f}"
            catalogid_groups = f"{(catalogid // k) % k:0>2.0f}/{catalogid % k:0>2.0f}"

            log.warn("hard-coding in path")
            from astra.utils import expand_path
            return expand_path("$MWM_ASTRA/{v_astra}/{run2d}-{apred}/results/star/{catalogid_groups}/astraStar-{pipeline}-{v_astra}-{cat_id}-{task_id}.fits".format(pipeline=pipeline, catalogid_groups=catalogid_groups, **self.kwargs))
        '''

        try:
            p = _sdss_path_instances[self.release]
        except KeyError:
            p = _sdss_path_instances[self.release] = SDSSPath(self.release)
        return p.full(self.filetype, **self.kwargs)

    @property
    def sources(self):
        return (
            Source.select()
            .join(SourceDataProduct)
            .join(DataProduct)
            .where(DataProduct.id == self.id)
        )


# DataProducts and Sources should be a many-to-many relationship.
class SourceDataProduct(AstraBaseModel):
    id = AutoField()
    source = ForeignKeyField(Source)
    data_product = ForeignKeyField(DataProduct)

    class Meta:
        indexes = (
            # Always remember to put the comma at the end.
            (("source", "data_product"), True),
        )


class Output(AstraBaseModel):
    id = AutoField()
    created = DateTimeField(default=datetime.datetime.now)


class Status(AstraBaseModel):
    id = AutoField()
    description = TextField()

    class Meta:
        indexes = (
            # Always remember to put the comma at the end.
            (("id", "description"), True),
        )


class Task(AstraBaseModel):
    id = AutoField()
    name = TextField()
    parameters = JSONField(default={})
    version = TextField(default=__version__)

    time_total = FloatField(null=True)
    time_pre_execute = FloatField(null=True)
    time_execute = FloatField(null=True)
    time_post_execute = FloatField(null=True)

    time_pre_execute_task = FloatField(null=True)
    time_pre_execute_bundle_overhead = FloatField(null=True)

    time_execute_task = FloatField(null=True)
    time_execute_bundle_overhead = FloatField(null=True)

    time_post_execute_task = FloatField(null=True)
    time_post_execute_bundle_overhead = FloatField(null=True)

    created = DateTimeField(default=datetime.datetime.now)
    completed = DateTimeField(null=True)

    status = ForeignKeyField(
        Status, default=1
    )  # default: 1 is the lowest status level ('created' or similar)

    def instance(self, strict=True):
        """Return an executable representation of this task."""

        from astra.base import TaskInstance

        return TaskInstance.from_task(self, strict=strict)

    @property
    def input_data_products(self):
        return (
            DataProduct.select()
            .join(TaskInputDataProducts)
            .join(Task)
            .where(Task.id == self.id)
        )

    @property
    def output_data_products(self):
        return (
            DataProduct.select()
            .join(TaskOutputDataProducts)
            .join(Task)
            .where(Task.id == self.id)
        )

    @property
    def outputs(self):
        """
        q = None
        # Create a compound union query to retrieve all possible outputs for this task.
        o = TaskOutput.get(TaskOutput.task == self)
        for expr, column in o.output.dependencies():
            if column.model != TaskOutput:def
                sq = column.model.select().where(column.model.task == self)
                if q is None:
                    q = sq
                else:
                    q += sq
        # Order by the order they were created.
        return q#.order_by(SQL("output_id").asc())
        """
        outputs = []
        o = TaskOutput.get(TaskOutput.task == self)
        for expr, column in o.output.dependencies():
            if column.model not in (TaskOutput, AstraOutputBaseModel):
                outputs.extend(column.model.select().where(column.model.task == self))
        return sorted(outputs, key=lambda x: x.output_id)

    def count_outputs(self):
        return TaskOutput.select().where(TaskOutput.task == self).count()

    def create_or_update_outputs(
        self, model, results, delete_existing_unused_outputs=True
    ):
        """
        Create outputs in the database (or update existing ones) for this task.

        :param model:
            The output model table (e.g., `astra.database.astradb.ApogeeNetOutput`).

        :param results:
            A list of dictionaries, where each dictionary represents an output row.

        :param delete_existing_unusued_outputs: [optional]
            Delete any existing output rows for this task that are no longer used (default: True).
        """

        existing_outputs = list(
            model.select()
            .where(model.task == self)
            .order_by(model.output_id.asc())
        )

        # Update existing outputs.
        N_existing = len(existing_outputs)
        N_results = len(results)

        if N_existing > 0:
            with database.atomic():
                fields = []
                for output, result in zip(existing_outputs, results):
                    for key, value in result.items():
                        if key in model._meta.fields and value is not None: # this skips over things like source_id, output_id, which wouldn't change
                            setattr(output, key, value)
                            fields.append(key)
                fields = list(set(fields))
                model.bulk_update(existing_outputs[:N_results], fields)

            log.info(f"Updated {min(N_existing, N_results)} existing results in {model}")

        N_new_results = N_results - N_existing
        if N_new_results > 0:
            new_outputs = [Output() for i in range(N_new_results)]
            with database.atomic():
                Output.bulk_create(new_outputs)
                TaskOutput.insert_many([
                    {"task_id": self.id, "output_id": o.id} for o in new_outputs
                ]).execute()

            # Now create the model new_outputs.
            with database.atomic():
                model.insert_many([
                    {"task_id": self.id, "output_id": o.id, **r} for o, r in zip(new_outputs, results[N_existing:])
                ]).execute()
            
            log.info(f"Created {N_new_results} new results in {model}")

        if delete_existing_unused_outputs and N_existing > N_results:
            unused_output_ids = [o.output_id for o in existing_outputs[N_results:]]
            with database.atomic():
                model.delete().where(model.output_id.in_(unused_output_ids)).execute()
                TaskOutput.delete().where(
                    TaskOutput.output_id.in_(unused_output_ids)
                ).execute()
                Output.delete().where(Output.id.in_(unused_output_ids)).execute()
            log.info(f"Deleted {len(unused_output_ids)} existing unused results in {model}")
        
        return None


class TaskOutput(AstraBaseModel):
    id = AutoField()
    task = ForeignKeyField(Task)
    output = ForeignKeyField(Output)


class Bundle(AstraBaseModel):
    id = AutoField()
    status = ForeignKeyField(
        Status, default=1
    )  # default: 1 is the lowest status level ('created' or similar)
    meta = JSONField(default={})

    @property
    def tasks(self):
        return Task.select().join(TaskBundle).join(Bundle).where(Bundle.id == self.id)


    def watch_status(self, interval=1):
        total = self.count_tasks()
        q = dict(
            Task
            .select(Task.status_id, fn.COUNT(Task.id))
            .join(TaskBundle)
            .where(TaskBundle.bundle_id == self.id)
            .group_by(Task.status_id)
            .tuples()
        )
        initial = q.get(5, 0)
        with tqdm(total=total, initial=initial) as pb:
            while True:
                sleep(interval)
                q = dict(
                    Task
                    .select(Task.status_id, fn.COUNT(Task.id))
                    .join(TaskBundle)
                    .where(TaskBundle.bundle_id == self.id)
                    .group_by(Task.status_id)
                    .tuples()
                )
                complete = q.get(5, 0)
                if complete > pb.n:
                    pb.update(complete - pb.n)
                if complete >= total:
                    break
        
        return None


    def _watch(self, interval=1):
        """
        Watch the progress of this bundle being executed (perhaps by some other executor).

        Progress is measured by the number of tasks with at least one TaskOutput, divided
        by the total number of tasks.
        """
        T = self.count_tasks()
        N = self.count_tasks_with_outputs()
        with tqdm(total=T, initial=N) as pb:
            while True:
                sleep(interval)
                M = self.count_tasks_with_outputs()
                if M > pb.n:
                    pb.update(M - pb.n)
                if M >= T:
                    break
        return None

    def count_tasks_with_outputs(self):
        return (
            TaskOutput.select()
            .distinct(TaskOutput.task)
            .where(TaskOutput.task.in_(self.tasks))
            .count()
        )

    def count_tasks(self):
        return self.tasks.count()

    def count_input_data_products(self):
        return (
            DataProduct.select()
            .join(TaskInputDataProducts)
            .join(Task)
            .join(TaskBundle)
            .where(TaskBundle.bundle_id == self.id)
            .count()
        )

    def count_input_data_products_size(self):
        (count,) = (
            DataProduct.select(fn.SUM(DataProduct.size))
            .join(TaskInputDataProducts)
            .join(Task)
            .join(TaskBundle)
            .join(Bundle)
            .where(Bundle.id == self.id)
            .tuples()
            .first()
        )
        return count

    def instance(self, only_incomplete=False, strict=True):
        from astra.base import TaskInstance
        return TaskInstance.from_bundle(self, only_incomplete=only_incomplete, strict=strict)

    def split(self, N):
        N = int(N)
        if N < 2:
            raise ValueError(f"N > 1")

        tasks = list(self.tasks)
        T = len(tasks)
        new_bundle_size = 1 + int(T / N)
        log.debug(f"Splitting bundle {self} into {N} smaller bundles")

        new_bundles = []
        for i in range(N):
            si = i * new_bundle_size
            ei = (i + 1) * new_bundle_size

            bundle = Bundle.create()
            for task in tasks[si:ei]:
                TaskBundle.create(task=task, bundle=bundle)
            new_bundles.append(bundle)
        return new_bundles



class TaskBundle(AstraBaseModel):
    id = AutoField()
    task = ForeignKeyField(Task, on_delete="CASCADE")
    bundle = ForeignKeyField(Bundle, on_delete="CASCADE")


class TaskInputDataProducts(AstraBaseModel):
    id = AutoField()
    task = ForeignKeyField(Task, on_delete="CASCADE")
    data_product = ForeignKeyField(DataProduct, on_delete="CASCADE")


class TaskOutputDataProducts(AstraBaseModel):
    id = AutoField()
    task = ForeignKeyField(Task, on_delete="CASCADE")
    data_product = ForeignKeyField(DataProduct, on_delete="CASCADE")


class AstraOutputBaseModel(AstraBaseModel):

    """A base class for output data models."""

    pass


class MWMSourceStatus(AstraOutputBaseModel):

    output = ForeignKeyField(Output, on_delete="CASCADE", primary_key=True)
    source = ForeignKeyField(Source)
    task = ForeignKeyField(Task)
    meta = JSONField(null=True)

    num_apogee_apo_visits = IntegerField(default=0)
    num_apogee_lco_visits = IntegerField(default=0)
    num_boss_apo_visits = IntegerField(default=0)
    num_boss_lco_visits = IntegerField(default=0)

    num_apogee_apo_visits_in_stack = IntegerField(default=0)
    num_apogee_lco_visits_in_stack = IntegerField(default=0)
    num_boss_apo_visits_in_stack = IntegerField(default=0)
    num_boss_lco_visits_in_stack = IntegerField(default=0)

    obs_start_apogee_apo = DateTimeField(null=True)
    obs_end_apogee_apo = DateTimeField(null=True)
    obs_start_apogee_lco = DateTimeField(null=True)
    obs_end_apogee_lco = DateTimeField(null=True)

    obs_start_boss_apo = DateTimeField(null=True)
    obs_end_boss_apo = DateTimeField(null=True)
    obs_start_boss_lco = DateTimeField(null=True)
    obs_end_boss_lco = DateTimeField(null=True)

    updated = DateTimeField(default=datetime.datetime.now)


# Output tables.
SMALL = -1e-20


class ClassifierOutput(AstraOutputBaseModel):

    output = ForeignKeyField(Output, on_delete="CASCADE", primary_key=True)
    task = ForeignKeyField(Task)
    meta = JSONField(null=True)
    source = ForeignKeyField(Source, null=True)
    parent_data_product = ForeignKeyField(DataProduct, null=True)

    dithered = BooleanField()

    snr = FloatField()
    p_cv = FloatField(default=0)
    lp_cv = FloatField(default=SMALL)
    p_fgkm = FloatField(default=0)
    lp_fgkm = FloatField(default=SMALL)
    p_hotstar = FloatField(default=0)
    lp_hotstar = FloatField(default=SMALL)
    p_wd = FloatField(default=0)
    lp_wd = FloatField(default=SMALL)
    p_sb2 = FloatField(default=0)
    lp_sb2 = FloatField(default=SMALL)
    p_yso = FloatField(default=0)
    lp_yso = FloatField(default=SMALL)


class ClassifySourceOutput(AstraOutputBaseModel):

    output = ForeignKeyField(Output, on_delete="CASCADE", primary_key=True)
    task = ForeignKeyField(Task)
    meta = JSONField(null=True)
    source = ForeignKeyField(Source, null=True)

    p_cv = FloatField(default=0)
    lp_cv = FloatField(default=SMALL)
    p_fgkm = FloatField(default=0)
    lp_fgkm = FloatField(default=SMALL)
    p_hotstar = FloatField(default=0)
    lp_hotstar = FloatField(default=SMALL)
    p_wd = FloatField(default=0)
    lp_wd = FloatField(default=SMALL)
    p_sb2 = FloatField(default=0)
    lp_sb2 = FloatField(default=SMALL)
    p_yso = FloatField(default=0)
    lp_yso = FloatField(default=SMALL)


class FerreOutput(AstraOutputBaseModel):

    output = ForeignKeyField(Output, on_delete="CASCADE", primary_key=True)
    task = ForeignKeyField(Task)
    meta = JSONField(null=True)
    source = ForeignKeyField(Source, null=True)
    parent_data_product = ForeignKeyField(DataProduct, null=True)

    snr = FloatField()
    teff = FloatField()
    logg = FloatField()
    metals = FloatField()
    lgvsini = FloatField(null=True)
    # BA grid doesn't use these:
    log10vdop = FloatField(null=True)
    o_mg_si_s_ca_ti = FloatField(null=True)
    c = FloatField(null=True)
    n = FloatField(null=True)

    e_teff = FloatField()
    e_logg = FloatField()
    e_metals = FloatField()
    e_log10vdop = FloatField(null=True)
    e_lgvsini = FloatField(null=True)
    e_o_mg_si_s_ca_ti = FloatField(null=True)
    e_c = FloatField(null=True)
    e_n = FloatField(null=True)

    bitmask_teff = IntegerField(default=0)
    bitmask_logg = IntegerField(default=0)
    bitmask_metals = IntegerField(default=0)
    bitmask_log10vdop = IntegerField(default=0)
    bitmask_lgvsini = IntegerField(default=0)
    bitmask_o_mg_si_s_ca_ti = IntegerField(default=0)
    bitmask_c = IntegerField(default=0)
    bitmask_n = IntegerField(default=0)

    log_chisq_fit = FloatField()
    log_snr_sq = FloatField()
    frac_phot_data_points = FloatField(default=0)

    # This penalized log chisq term is strictly a term defined and used by ASPCAP
    # and not FERRE, but it is easier to understand what is happening when selecting
    # the `best` model if we have a penalized \chisq term.
    penalized_log_chisq_fit = FloatField(null=True)

    # Astra records the time taken *per task*, and infers things like overhead time for each stage
    # of pre_execute, execute, and post_execute.
    # But even one task with a single data model could contain many spectra that we analyse with
    # FERRE, and for performance purposes we want to know the time taken by FERRE.
    # For these reasons, let's store some metadata here, even if we could infer it from other things.
    ferre_time_elapsed = FloatField(null=True)
    ferre_time_load = FloatField(null=True)
    ferre_n_threads = IntegerField(null=True)
    ferre_n_obj = IntegerField(null=True)


class ApogeeNetOutput(AstraOutputBaseModel):

    output = ForeignKeyField(Output, on_delete="CASCADE", primary_key=True)
    task = ForeignKeyField(Task)
    meta = JSONField(null=True)
    source = ForeignKeyField(Source, null=True)
    parent_data_product = ForeignKeyField(DataProduct, null=True)

    snr = FloatField()
    teff = FloatField()
    logg = FloatField()
    fe_h = FloatField()
    e_teff = FloatField()
    e_logg = FloatField()
    e_fe_h = FloatField()
    teff_sample_median = FloatField()
    logg_sample_median = FloatField()
    fe_h_sample_median = FloatField()
    bitmask_flag = IntegerField(default=0)


class AspcapOutput(AstraOutputBaseModel):

    output = ForeignKeyField(Output, on_delete="CASCADE", primary_key=True)
    task = ForeignKeyField(Task)
    meta = JSONField(null=True)
    source = ForeignKeyField(Source, null=True)
    parent_data_product = ForeignKeyField(DataProduct, null=True)

    # Metadata.
    snr = FloatField()


# Dynamically add many fields to AspcapOutput.
sp_field_names = (
    "teff",
    "logg",
    "metals",
    "log10vdop",
    "o_mg_si_s_ca_ti",
    "lgvsini",
    "c",
    "n",
)
null_field_names = ("lgvsini", "log10vdop", "o_mg_si_s_ca_ti", "c", "n")
elements = (
    "cn",
    "al",
    "ca",
    "ce",
    "co",
    "cr",
    "fe",
    "k",
    "mg",
    "mn",
    "na",
    "nd",
    "ni",
    "o",
    "p",
    "rb",
    "si",
    "s",
    "ti",
    "v",
    "yb",
)

for field_name in sp_field_names:
    null = field_name in null_field_names
    AspcapOutput._meta.add_field(field_name, FloatField(null=null))
    AspcapOutput._meta.add_field(f"e_{field_name}", FloatField(null=null))
    AspcapOutput._meta.add_field(f"bitmask_{field_name}", IntegerField(default=0))

AspcapOutput._meta.add_field("log_chisq_fit", FloatField())
AspcapOutput._meta.add_field("log_snr_sq", FloatField())

# All element fields can be null, and they need their own log_chisq_fit
for element in elements:
    AspcapOutput._meta.add_field(f"{element}_h", FloatField(null=True))
    AspcapOutput._meta.add_field(f"e_{element}_h", FloatField(null=True))
    AspcapOutput._meta.add_field(f"bitmask_{element}_h", IntegerField(default=0))
    AspcapOutput._meta.add_field(f"log_chisq_fit_{element}_h", FloatField(null=True))


class TheCannonOutput(AstraOutputBaseModel):

    output = ForeignKeyField(Output, on_delete="CASCADE", primary_key=True)
    task = ForeignKeyField(Task)
    meta = JSONField(null=True)
    source = ForeignKeyField(Source, null=True)
    parent_data_product = ForeignKeyField(DataProduct, null=True)

    # Metadata.
    snr = FloatField()
    bitmask_flag = IntegerField(default=0)
    chi_sq = FloatField()
    reduced_chi_sq = FloatField()

    teff = FloatField()
    e_teff = FloatField()
    logg = FloatField()
    e_logg = FloatField()
    fe_h = FloatField()
    e_fe_h = FloatField()
    c_h = FloatField()
    e_c_h = FloatField()
    n_h = FloatField()
    e_n_h = FloatField()
    o_h = FloatField()
    e_o_h = FloatField()
    na_h = FloatField()
    e_na_h = FloatField()
    mg_h = FloatField()
    e_mg_h = FloatField()
    al_h = FloatField()
    e_al_h = FloatField()
    si_h = FloatField()
    e_si_h = FloatField()
    s_h = FloatField()
    e_s_h = FloatField()
    k_h = FloatField()
    e_k_h = FloatField()
    ca_h = FloatField()
    e_ca_h = FloatField()
    ti_h = FloatField()
    e_ti_h = FloatField()
    v_h = FloatField()
    e_v_h = FloatField()
    cr_h = FloatField()
    e_cr_h = FloatField()
    mn_h = FloatField()
    e_mn_h = FloatField()
    co_h = FloatField()
    e_co_h = FloatField()
    ni_h = FloatField()
    e_ni_h = FloatField()

    rho_teff_logg = FloatField(default=0)
    rho_teff_fe_h = FloatField(default=0)
    rho_logg_fe_h = FloatField(default=0)
    rho_teff_c_h = FloatField(default=0)
    rho_logg_c_h = FloatField(default=0)
    rho_fe_h_c_h = FloatField(default=0)
    rho_teff_n_h = FloatField(default=0)
    rho_logg_n_h = FloatField(default=0)
    rho_fe_h_n_h = FloatField(default=0)
    rho_c_h_n_h = FloatField(default=0)
    rho_teff_o_h = FloatField(default=0)
    rho_logg_o_h = FloatField(default=0)
    rho_fe_h_o_h = FloatField(default=0)
    rho_c_h_o_h = FloatField(default=0)
    rho_n_h_o_h = FloatField(default=0)
    rho_teff_na_h = FloatField(default=0)
    rho_logg_na_h = FloatField(default=0)
    rho_fe_h_na_h = FloatField(default=0)
    rho_c_h_na_h = FloatField(default=0)
    rho_n_h_na_h = FloatField(default=0)
    rho_o_h_na_h = FloatField(default=0)
    rho_teff_mg_h = FloatField(default=0)
    rho_logg_mg_h = FloatField(default=0)
    rho_fe_h_mg_h = FloatField(default=0)
    rho_c_h_mg_h = FloatField(default=0)
    rho_n_h_mg_h = FloatField(default=0)
    rho_o_h_mg_h = FloatField(default=0)
    rho_na_h_mg_h = FloatField(default=0)
    rho_teff_al_h = FloatField(default=0)
    rho_logg_al_h = FloatField(default=0)
    rho_fe_h_al_h = FloatField(default=0)
    rho_c_h_al_h = FloatField(default=0)
    rho_n_h_al_h = FloatField(default=0)
    rho_o_h_al_h = FloatField(default=0)
    rho_na_h_al_h = FloatField(default=0)
    rho_mg_h_al_h = FloatField(default=0)
    rho_teff_si_h = FloatField(default=0)
    rho_logg_si_h = FloatField(default=0)
    rho_fe_h_si_h = FloatField(default=0)
    rho_c_h_si_h = FloatField(default=0)
    rho_n_h_si_h = FloatField(default=0)
    rho_o_h_si_h = FloatField(default=0)
    rho_na_h_si_h = FloatField(default=0)
    rho_mg_h_si_h = FloatField(default=0)
    rho_al_h_si_h = FloatField(default=0)
    rho_teff_s_h = FloatField(default=0)
    rho_logg_s_h = FloatField(default=0)
    rho_fe_h_s_h = FloatField(default=0)
    rho_c_h_s_h = FloatField(default=0)
    rho_n_h_s_h = FloatField(default=0)
    rho_o_h_s_h = FloatField(default=0)
    rho_na_h_s_h = FloatField(default=0)
    rho_mg_h_s_h = FloatField(default=0)
    rho_al_h_s_h = FloatField(default=0)
    rho_si_h_s_h = FloatField(default=0)
    rho_teff_k_h = FloatField(default=0)
    rho_logg_k_h = FloatField(default=0)
    rho_fe_h_k_h = FloatField(default=0)
    rho_c_h_k_h = FloatField(default=0)
    rho_n_h_k_h = FloatField(default=0)
    rho_o_h_k_h = FloatField(default=0)
    rho_na_h_k_h = FloatField(default=0)
    rho_mg_h_k_h = FloatField(default=0)
    rho_al_h_k_h = FloatField(default=0)
    rho_si_h_k_h = FloatField(default=0)
    rho_s_h_k_h = FloatField(default=0)
    rho_teff_ca_h = FloatField(default=0)
    rho_logg_ca_h = FloatField(default=0)
    rho_fe_h_ca_h = FloatField(default=0)
    rho_c_h_ca_h = FloatField(default=0)
    rho_n_h_ca_h = FloatField(default=0)
    rho_o_h_ca_h = FloatField(default=0)
    rho_na_h_ca_h = FloatField(default=0)
    rho_mg_h_ca_h = FloatField(default=0)
    rho_al_h_ca_h = FloatField(default=0)
    rho_si_h_ca_h = FloatField(default=0)
    rho_s_h_ca_h = FloatField(default=0)
    rho_k_h_ca_h = FloatField(default=0)
    rho_teff_ti_h = FloatField(default=0)
    rho_logg_ti_h = FloatField(default=0)
    rho_fe_h_ti_h = FloatField(default=0)
    rho_c_h_ti_h = FloatField(default=0)
    rho_n_h_ti_h = FloatField(default=0)
    rho_o_h_ti_h = FloatField(default=0)
    rho_na_h_ti_h = FloatField(default=0)
    rho_mg_h_ti_h = FloatField(default=0)
    rho_al_h_ti_h = FloatField(default=0)
    rho_si_h_ti_h = FloatField(default=0)
    rho_s_h_ti_h = FloatField(default=0)
    rho_k_h_ti_h = FloatField(default=0)
    rho_ca_h_ti_h = FloatField(default=0)
    rho_teff_v_h = FloatField(default=0)
    rho_logg_v_h = FloatField(default=0)
    rho_fe_h_v_h = FloatField(default=0)
    rho_c_h_v_h = FloatField(default=0)
    rho_n_h_v_h = FloatField(default=0)
    rho_o_h_v_h = FloatField(default=0)
    rho_na_h_v_h = FloatField(default=0)
    rho_mg_h_v_h = FloatField(default=0)
    rho_al_h_v_h = FloatField(default=0)
    rho_si_h_v_h = FloatField(default=0)
    rho_s_h_v_h = FloatField(default=0)
    rho_k_h_v_h = FloatField(default=0)
    rho_ca_h_v_h = FloatField(default=0)
    rho_ti_h_v_h = FloatField(default=0)
    rho_teff_cr_h = FloatField(default=0)
    rho_logg_cr_h = FloatField(default=0)
    rho_fe_h_cr_h = FloatField(default=0)
    rho_c_h_cr_h = FloatField(default=0)
    rho_n_h_cr_h = FloatField(default=0)
    rho_o_h_cr_h = FloatField(default=0)
    rho_na_h_cr_h = FloatField(default=0)
    rho_mg_h_cr_h = FloatField(default=0)
    rho_al_h_cr_h = FloatField(default=0)
    rho_si_h_cr_h = FloatField(default=0)
    rho_s_h_cr_h = FloatField(default=0)
    rho_k_h_cr_h = FloatField(default=0)
    rho_ca_h_cr_h = FloatField(default=0)
    rho_ti_h_cr_h = FloatField(default=0)
    rho_v_h_cr_h = FloatField(default=0)
    rho_teff_mn_h = FloatField(default=0)
    rho_logg_mn_h = FloatField(default=0)
    rho_fe_h_mn_h = FloatField(default=0)
    rho_c_h_mn_h = FloatField(default=0)
    rho_n_h_mn_h = FloatField(default=0)
    rho_o_h_mn_h = FloatField(default=0)
    rho_na_h_mn_h = FloatField(default=0)
    rho_mg_h_mn_h = FloatField(default=0)
    rho_al_h_mn_h = FloatField(default=0)
    rho_si_h_mn_h = FloatField(default=0)
    rho_s_h_mn_h = FloatField(default=0)
    rho_k_h_mn_h = FloatField(default=0)
    rho_ca_h_mn_h = FloatField(default=0)
    rho_ti_h_mn_h = FloatField(default=0)
    rho_v_h_mn_h = FloatField(default=0)
    rho_cr_h_mn_h = FloatField(default=0)
    rho_teff_co_h = FloatField(default=0)
    rho_logg_co_h = FloatField(default=0)
    rho_fe_h_co_h = FloatField(default=0)
    rho_c_h_co_h = FloatField(default=0)
    rho_n_h_co_h = FloatField(default=0)
    rho_o_h_co_h = FloatField(default=0)
    rho_na_h_co_h = FloatField(default=0)
    rho_mg_h_co_h = FloatField(default=0)
    rho_al_h_co_h = FloatField(default=0)
    rho_si_h_co_h = FloatField(default=0)
    rho_s_h_co_h = FloatField(default=0)
    rho_k_h_co_h = FloatField(default=0)
    rho_ca_h_co_h = FloatField(default=0)
    rho_ti_h_co_h = FloatField(default=0)
    rho_v_h_co_h = FloatField(default=0)
    rho_cr_h_co_h = FloatField(default=0)
    rho_mn_h_co_h = FloatField(default=0)
    rho_teff_ni_h = FloatField(default=0)
    rho_logg_ni_h = FloatField(default=0)
    rho_fe_h_ni_h = FloatField(default=0)
    rho_c_h_ni_h = FloatField(default=0)
    rho_n_h_ni_h = FloatField(default=0)
    rho_o_h_ni_h = FloatField(default=0)
    rho_na_h_ni_h = FloatField(default=0)
    rho_mg_h_ni_h = FloatField(default=0)
    rho_al_h_ni_h = FloatField(default=0)
    rho_si_h_ni_h = FloatField(default=0)
    rho_s_h_ni_h = FloatField(default=0)
    rho_k_h_ni_h = FloatField(default=0)
    rho_ca_h_ni_h = FloatField(default=0)
    rho_ti_h_ni_h = FloatField(default=0)
    rho_v_h_ni_h = FloatField(default=0)
    rho_cr_h_ni_h = FloatField(default=0)
    rho_mn_h_ni_h = FloatField(default=0)
    rho_co_h_ni_h = FloatField(default=0)


class ZetaPayneOutput(AstraOutputBaseModel):

    output = ForeignKeyField(Output, on_delete="CASCADE", primary_key=True)
    task = ForeignKeyField(Task)
    meta = JSONField(null=True)
    source = ForeignKeyField(Source, null=True)
    parent_data_product = ForeignKeyField(DataProduct, null=True)

    snr = FloatField()

    teff = FloatField(null=True)
    e_teff = FloatField(null=True)
    logg = FloatField(null=True)
    e_logg = FloatField(null=True)
    fe_h = FloatField(null=True)
    e_fe_h = FloatField(null=True)
    vsini = FloatField(null=True)
    e_vsini = FloatField(null=True)
    v_micro = FloatField(null=True)
    e_v_micro = FloatField(null=True)
    v_rel = FloatField(null=True)
    e_v_rel = FloatField(null=True)

    # continuum coefficients
    try:
        theta = ArrayField(FloatField)
    except:
        log.exception(f"Could not create ArrayField, ignoring..")

    chi_sq = FloatField()
    reduced_chi_sq = FloatField()



class ThePayneOutput(AstraOutputBaseModel):

    output = ForeignKeyField(Output, on_delete="CASCADE", primary_key=True)
    task = ForeignKeyField(Task)
    meta = JSONField(null=True)
    source = ForeignKeyField(Source, null=True)
    parent_data_product = ForeignKeyField(DataProduct, null=True)

    snr = FloatField()
    v_rad = FloatField(null=True)

    teff = FloatField()
    logg = FloatField()
    v_turb = FloatField()
    c_h = FloatField()
    n_h = FloatField()
    o_h = FloatField()
    na_h = FloatField()
    mg_h = FloatField()
    al_h = FloatField()
    si_h = FloatField()
    p_h = FloatField()
    s_h = FloatField()
    k_h = FloatField()
    ca_h = FloatField()
    ti_h = FloatField()
    v_h = FloatField()
    cr_h = FloatField()
    mn_h = FloatField()
    fe_h = FloatField()
    co_h = FloatField()
    ni_h = FloatField()
    cu_h = FloatField()
    ge_h = FloatField()
    c12_c13 = FloatField()
    v_macro = FloatField()
    e_teff = FloatField()
    e_logg = FloatField()
    e_v_turb = FloatField()
    e_c_h = FloatField()
    e_n_h = FloatField()
    e_o_h = FloatField()
    e_na_h = FloatField()
    e_mg_h = FloatField()
    e_al_h = FloatField()
    e_si_h = FloatField()
    e_p_h = FloatField()
    e_s_h = FloatField()
    e_k_h = FloatField()
    e_ca_h = FloatField()
    e_ti_h = FloatField()
    e_v_h = FloatField()
    e_cr_h = FloatField()
    e_mn_h = FloatField()
    e_fe_h = FloatField()
    e_co_h = FloatField()
    e_ni_h = FloatField()
    e_cu_h = FloatField()
    e_ge_h = FloatField()
    e_c12_c13 = FloatField()
    e_v_macro = FloatField()
    rho_teff_logg = FloatField()
    rho_teff_v_turb = FloatField()
    rho_teff_c_h = FloatField()
    rho_teff_n_h = FloatField()
    rho_teff_o_h = FloatField()
    rho_teff_na_h = FloatField()
    rho_teff_mg_h = FloatField()
    rho_teff_al_h = FloatField()
    rho_teff_si_h = FloatField()
    rho_teff_p_h = FloatField()
    rho_teff_s_h = FloatField()
    rho_teff_k_h = FloatField()
    rho_teff_ca_h = FloatField()
    rho_teff_ti_h = FloatField()
    rho_teff_v_h = FloatField()
    rho_teff_cr_h = FloatField()
    rho_teff_mn_h = FloatField()
    rho_teff_fe_h = FloatField()
    rho_teff_co_h = FloatField()
    rho_teff_ni_h = FloatField()
    rho_teff_cu_h = FloatField()
    rho_teff_ge_h = FloatField()
    rho_teff_c12_c13 = FloatField()
    rho_teff_v_macro = FloatField()
    rho_logg_v_turb = FloatField()
    rho_logg_c_h = FloatField()
    rho_logg_n_h = FloatField()
    rho_logg_o_h = FloatField()
    rho_logg_na_h = FloatField()
    rho_logg_mg_h = FloatField()
    rho_logg_al_h = FloatField()
    rho_logg_si_h = FloatField()
    rho_logg_p_h = FloatField()
    rho_logg_s_h = FloatField()
    rho_logg_k_h = FloatField()
    rho_logg_ca_h = FloatField()
    rho_logg_ti_h = FloatField()
    rho_logg_v_h = FloatField()
    rho_logg_cr_h = FloatField()
    rho_logg_mn_h = FloatField()
    rho_logg_fe_h = FloatField()
    rho_logg_co_h = FloatField()
    rho_logg_ni_h = FloatField()
    rho_logg_cu_h = FloatField()
    rho_logg_ge_h = FloatField()
    rho_logg_c12_c13 = FloatField()
    rho_logg_v_macro = FloatField()
    rho_v_turb_c_h = FloatField()
    rho_v_turb_n_h = FloatField()
    rho_v_turb_o_h = FloatField()
    rho_v_turb_na_h = FloatField()
    rho_v_turb_mg_h = FloatField()
    rho_v_turb_al_h = FloatField()
    rho_v_turb_si_h = FloatField()
    rho_v_turb_p_h = FloatField()
    rho_v_turb_s_h = FloatField()
    rho_v_turb_k_h = FloatField()
    rho_v_turb_ca_h = FloatField()
    rho_v_turb_ti_h = FloatField()
    rho_v_turb_v_h = FloatField()
    rho_v_turb_cr_h = FloatField()
    rho_v_turb_mn_h = FloatField()
    rho_v_turb_fe_h = FloatField()
    rho_v_turb_co_h = FloatField()
    rho_v_turb_ni_h = FloatField()
    rho_v_turb_cu_h = FloatField()
    rho_v_turb_ge_h = FloatField()
    rho_v_turb_c12_c13 = FloatField()
    rho_v_turb_v_macro = FloatField()
    rho_c_h_n_h = FloatField()
    rho_c_h_o_h = FloatField()
    rho_c_h_na_h = FloatField()
    rho_c_h_mg_h = FloatField()
    rho_c_h_al_h = FloatField()
    rho_c_h_si_h = FloatField()
    rho_c_h_p_h = FloatField()
    rho_c_h_s_h = FloatField()
    rho_c_h_k_h = FloatField()
    rho_c_h_ca_h = FloatField()
    rho_c_h_ti_h = FloatField()
    rho_c_h_v_h = FloatField()
    rho_c_h_cr_h = FloatField()
    rho_c_h_mn_h = FloatField()
    rho_c_h_fe_h = FloatField()
    rho_c_h_co_h = FloatField()
    rho_c_h_ni_h = FloatField()
    rho_c_h_cu_h = FloatField()
    rho_c_h_ge_h = FloatField()
    rho_c_h_c12_c13 = FloatField()
    rho_c_h_v_macro = FloatField()
    rho_n_h_o_h = FloatField()
    rho_n_h_na_h = FloatField()
    rho_n_h_mg_h = FloatField()
    rho_n_h_al_h = FloatField()
    rho_n_h_si_h = FloatField()
    rho_n_h_p_h = FloatField()
    rho_n_h_s_h = FloatField()
    rho_n_h_k_h = FloatField()
    rho_n_h_ca_h = FloatField()
    rho_n_h_ti_h = FloatField()
    rho_n_h_v_h = FloatField()
    rho_n_h_cr_h = FloatField()
    rho_n_h_mn_h = FloatField()
    rho_n_h_fe_h = FloatField()
    rho_n_h_co_h = FloatField()
    rho_n_h_ni_h = FloatField()
    rho_n_h_cu_h = FloatField()
    rho_n_h_ge_h = FloatField()
    rho_n_h_c12_c13 = FloatField()
    rho_n_h_v_macro = FloatField()
    rho_o_h_na_h = FloatField()
    rho_o_h_mg_h = FloatField()
    rho_o_h_al_h = FloatField()
    rho_o_h_si_h = FloatField()
    rho_o_h_p_h = FloatField()
    rho_o_h_s_h = FloatField()
    rho_o_h_k_h = FloatField()
    rho_o_h_ca_h = FloatField()
    rho_o_h_ti_h = FloatField()
    rho_o_h_v_h = FloatField()
    rho_o_h_cr_h = FloatField()
    rho_o_h_mn_h = FloatField()
    rho_o_h_fe_h = FloatField()
    rho_o_h_co_h = FloatField()
    rho_o_h_ni_h = FloatField()
    rho_o_h_cu_h = FloatField()
    rho_o_h_ge_h = FloatField()
    rho_o_h_c12_c13 = FloatField()
    rho_o_h_v_macro = FloatField()
    rho_na_h_mg_h = FloatField()
    rho_na_h_al_h = FloatField()
    rho_na_h_si_h = FloatField()
    rho_na_h_p_h = FloatField()
    rho_na_h_s_h = FloatField()
    rho_na_h_k_h = FloatField()
    rho_na_h_ca_h = FloatField()
    rho_na_h_ti_h = FloatField()
    rho_na_h_v_h = FloatField()
    rho_na_h_cr_h = FloatField()
    rho_na_h_mn_h = FloatField()
    rho_na_h_fe_h = FloatField()
    rho_na_h_co_h = FloatField()
    rho_na_h_ni_h = FloatField()
    rho_na_h_cu_h = FloatField()
    rho_na_h_ge_h = FloatField()
    rho_na_h_c12_c13 = FloatField()
    rho_na_h_v_macro = FloatField()
    rho_mg_h_al_h = FloatField()
    rho_mg_h_si_h = FloatField()
    rho_mg_h_p_h = FloatField()
    rho_mg_h_s_h = FloatField()
    rho_mg_h_k_h = FloatField()
    rho_mg_h_ca_h = FloatField()
    rho_mg_h_ti_h = FloatField()
    rho_mg_h_v_h = FloatField()
    rho_mg_h_cr_h = FloatField()
    rho_mg_h_mn_h = FloatField()
    rho_mg_h_fe_h = FloatField()
    rho_mg_h_co_h = FloatField()
    rho_mg_h_ni_h = FloatField()
    rho_mg_h_cu_h = FloatField()
    rho_mg_h_ge_h = FloatField()
    rho_mg_h_c12_c13 = FloatField()
    rho_mg_h_v_macro = FloatField()
    rho_al_h_si_h = FloatField()
    rho_al_h_p_h = FloatField()
    rho_al_h_s_h = FloatField()
    rho_al_h_k_h = FloatField()
    rho_al_h_ca_h = FloatField()
    rho_al_h_ti_h = FloatField()
    rho_al_h_v_h = FloatField()
    rho_al_h_cr_h = FloatField()
    rho_al_h_mn_h = FloatField()
    rho_al_h_fe_h = FloatField()
    rho_al_h_co_h = FloatField()
    rho_al_h_ni_h = FloatField()
    rho_al_h_cu_h = FloatField()
    rho_al_h_ge_h = FloatField()
    rho_al_h_c12_c13 = FloatField()
    rho_al_h_v_macro = FloatField()
    rho_si_h_p_h = FloatField()
    rho_si_h_s_h = FloatField()
    rho_si_h_k_h = FloatField()
    rho_si_h_ca_h = FloatField()
    rho_si_h_ti_h = FloatField()
    rho_si_h_v_h = FloatField()
    rho_si_h_cr_h = FloatField()
    rho_si_h_mn_h = FloatField()
    rho_si_h_fe_h = FloatField()
    rho_si_h_co_h = FloatField()
    rho_si_h_ni_h = FloatField()
    rho_si_h_cu_h = FloatField()
    rho_si_h_ge_h = FloatField()
    rho_si_h_c12_c13 = FloatField()
    rho_si_h_v_macro = FloatField()
    rho_p_h_s_h = FloatField()
    rho_p_h_k_h = FloatField()
    rho_p_h_ca_h = FloatField()
    rho_p_h_ti_h = FloatField()
    rho_p_h_v_h = FloatField()
    rho_p_h_cr_h = FloatField()
    rho_p_h_mn_h = FloatField()
    rho_p_h_fe_h = FloatField()
    rho_p_h_co_h = FloatField()
    rho_p_h_ni_h = FloatField()
    rho_p_h_cu_h = FloatField()
    rho_p_h_ge_h = FloatField()
    rho_p_h_c12_c13 = FloatField()
    rho_p_h_v_macro = FloatField()
    rho_s_h_k_h = FloatField()
    rho_s_h_ca_h = FloatField()
    rho_s_h_ti_h = FloatField()
    rho_s_h_v_h = FloatField()
    rho_s_h_cr_h = FloatField()
    rho_s_h_mn_h = FloatField()
    rho_s_h_fe_h = FloatField()
    rho_s_h_co_h = FloatField()
    rho_s_h_ni_h = FloatField()
    rho_s_h_cu_h = FloatField()
    rho_s_h_ge_h = FloatField()
    rho_s_h_c12_c13 = FloatField()
    rho_s_h_v_macro = FloatField()
    rho_k_h_ca_h = FloatField()
    rho_k_h_ti_h = FloatField()
    rho_k_h_v_h = FloatField()
    rho_k_h_cr_h = FloatField()
    rho_k_h_mn_h = FloatField()
    rho_k_h_fe_h = FloatField()
    rho_k_h_co_h = FloatField()
    rho_k_h_ni_h = FloatField()
    rho_k_h_cu_h = FloatField()
    rho_k_h_ge_h = FloatField()
    rho_k_h_c12_c13 = FloatField()
    rho_k_h_v_macro = FloatField()
    rho_ca_h_ti_h = FloatField()
    rho_ca_h_v_h = FloatField()
    rho_ca_h_cr_h = FloatField()
    rho_ca_h_mn_h = FloatField()
    rho_ca_h_fe_h = FloatField()
    rho_ca_h_co_h = FloatField()
    rho_ca_h_ni_h = FloatField()
    rho_ca_h_cu_h = FloatField()
    rho_ca_h_ge_h = FloatField()
    rho_ca_h_c12_c13 = FloatField()
    rho_ca_h_v_macro = FloatField()
    rho_ti_h_v_h = FloatField()
    rho_ti_h_cr_h = FloatField()
    rho_ti_h_mn_h = FloatField()
    rho_ti_h_fe_h = FloatField()
    rho_ti_h_co_h = FloatField()
    rho_ti_h_ni_h = FloatField()
    rho_ti_h_cu_h = FloatField()
    rho_ti_h_ge_h = FloatField()
    rho_ti_h_c12_c13 = FloatField()
    rho_ti_h_v_macro = FloatField()
    rho_v_h_cr_h = FloatField()
    rho_v_h_mn_h = FloatField()
    rho_v_h_fe_h = FloatField()
    rho_v_h_co_h = FloatField()
    rho_v_h_ni_h = FloatField()
    rho_v_h_cu_h = FloatField()
    rho_v_h_ge_h = FloatField()
    rho_v_h_c12_c13 = FloatField()
    rho_v_h_v_macro = FloatField()
    rho_cr_h_mn_h = FloatField()
    rho_cr_h_fe_h = FloatField()
    rho_cr_h_co_h = FloatField()
    rho_cr_h_ni_h = FloatField()
    rho_cr_h_cu_h = FloatField()
    rho_cr_h_ge_h = FloatField()
    rho_cr_h_c12_c13 = FloatField()
    rho_cr_h_v_macro = FloatField()
    rho_mn_h_fe_h = FloatField()
    rho_mn_h_co_h = FloatField()
    rho_mn_h_ni_h = FloatField()
    rho_mn_h_cu_h = FloatField()
    rho_mn_h_ge_h = FloatField()
    rho_mn_h_c12_c13 = FloatField()
    rho_mn_h_v_macro = FloatField()
    rho_fe_h_co_h = FloatField()
    rho_fe_h_ni_h = FloatField()
    rho_fe_h_cu_h = FloatField()
    rho_fe_h_ge_h = FloatField()
    rho_fe_h_c12_c13 = FloatField()
    rho_fe_h_v_macro = FloatField()
    rho_co_h_ni_h = FloatField()
    rho_co_h_cu_h = FloatField()
    rho_co_h_ge_h = FloatField()
    rho_co_h_c12_c13 = FloatField()
    rho_co_h_v_macro = FloatField()
    rho_ni_h_cu_h = FloatField()
    rho_ni_h_ge_h = FloatField()
    rho_ni_h_c12_c13 = FloatField()
    rho_ni_h_v_macro = FloatField()
    rho_cu_h_ge_h = FloatField()
    rho_cu_h_c12_c13 = FloatField()
    rho_cu_h_v_macro = FloatField()
    rho_ge_h_c12_c13 = FloatField()
    rho_ge_h_v_macro = FloatField()
    rho_c12_c13_v_macro = FloatField()

    chi_sq = FloatField()
    reduced_chi_sq = FloatField()
    bitmask_flag = IntegerField(default=0)


class WhiteDwarfOutput(AstraOutputBaseModel):

    output = ForeignKeyField(Output, on_delete="CASCADE", primary_key=True)
    task = ForeignKeyField(Task)
    meta = JSONField(null=True)
    source = ForeignKeyField(Source, null=True)
    parent_data_product = ForeignKeyField(DataProduct, null=True)

    wd_type = TextField()
    snr = FloatField()
    teff = FloatField()
    e_teff = FloatField()
    logg = FloatField()
    e_logg = FloatField()

    v_rel = FloatField()
    chi_sq = FloatField()
    reduced_chi_sq = FloatField()

    conditioned_on_parallax = FloatField(null=True)
    conditioned_on_phot_g_mean_mag = FloatField(null=True)


class WhiteDwarfLineRatiosOutput(AstraOutputBaseModel):

    output = ForeignKeyField(Output, on_delete="CASCADE", primary_key=True)
    task = ForeignKeyField(Task)
    meta = JSONField(null=True)
    source = ForeignKeyField(Source, null=True)
    parent_data_product = ForeignKeyField(DataProduct, null=True)

    wavelength_start = FloatField()
    wavelength_end = FloatField()
    line_ratio = FloatField()

class WhiteDwarfClassifierOutput(AstraOutputBaseModel):

    output = ForeignKeyField(Output, on_delete="CASCADE", primary_key=True)
    task = ForeignKeyField(Task)
    meta = JSONField(null=True)
    source = ForeignKeyField(Source, null=True)
    parent_data_product = ForeignKeyField(DataProduct, null=True)

    wd_type = TextField()
    

class SlamOutput(AstraOutputBaseModel):

    output = ForeignKeyField(Output, on_delete="CASCADE", primary_key=True)
    task = ForeignKeyField(Task)
    meta = JSONField(null=True)
    source = ForeignKeyField(Source, null=True)
    parent_data_product = ForeignKeyField(DataProduct, null=True)

    snr = FloatField()

    # Initial values.
    initial_teff = FloatField()
    initial_logg = FloatField()
    initial_fe_h = FloatField()

    # Labels.
    teff = FloatField()
    e_teff = FloatField()
    logg = FloatField()
    e_logg = FloatField()
    fe_h = FloatField()
    e_fe_h = FloatField()
    
    # Correlation coefficients.
    rho_teff_logg = FloatField()
    rho_teff_fe_h = FloatField()
    rho_logg_fe_h = FloatField()

    # Optimisation outputs.
    success = BooleanField()
    status = IntegerField()
    optimality = BooleanField()

    # Statistics.
    chi_sq = FloatField()
    reduced_chi_sq = FloatField()


def create_tables(
    drop_existing_tables=False,
    reuse_if_open=True,
    insert_status_rows=True,
):
    """
    Create all tables for the Astra database.

    :param drop_existing_tables: [optional]
        Drop existing tables from the database (default: false).

    :param reuse_if_open: [optional]
        Re-use existing database connection if one is open (default: true).

    :param insert_status_rows: [optional]
        Insert rows describing the Status of each task (default: true)
    """

    log.info(f"Connecting to database to create tables.")
    database.connect(reuse_if_open=reuse_if_open)
    models = AstraBaseModel.__subclasses__()
    models.extend(AstraOutputBaseModel.__subclasses__())
    log.info(
        f"Tables ({len(models)}): {', '.join([model.__name__ for model in models])}"
    )
    if drop_existing_tables:
        log.info(f"Dropping existing tables..")
        database.drop_tables(models)

    database.create_tables(models)

    # Put data in for Status
    if insert_status_rows:
        log.info(f"Inserting Status rows")
        # Note that the most important description here is the first one, which should be the
        # lowest level of the status hierarchy. This is because the default status for a Task
        # or Bundle is `id=1`, so whichever is the lowest level of the hierarchy.
        status_descriptions = [
            "created",
            "locked",
            "submitted",
            "running",
            "completed",
            "failed-pre-execution",
            "failed-execution",
            "failed-post-execution",
        ]
        with database.atomic():
            for description in status_descriptions:
                Status.create(description=description)
    log.info(f"Done.")
    return None
