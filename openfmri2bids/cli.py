import click
from converter import convert


@click.command()
@click.argument('openfmri_dataset_path', required=True, type=click.Path(exists=True))
@click.argument('output_folder', required=True, type=click.Path())
def main(openfmri_dataset_path, output_folder):
    """Convert OpenfMRI dataset to BIDS."""
    click.echo('{0}, {1}.'.format(openfmri_dataset_path, output_folder))
    
    convert(openfmri_dataset_path, output_folder, empty_nii=True)


if __name__ == '__main__':
    main()