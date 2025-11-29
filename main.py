"""
Main entry point for the Jira scraping and transformation pipeline.
"""
import logging
import sys
from pathlib import Path
from scraper.data_scraper import DataScraper
from transformer.data_transformer import DataTransformer
from utils.state_manager import StateManager
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("Jira Scraping and Transformation Pipeline")
    logger.info("=" * 60)
    
    # Initialize components
    logger.info("Initializing components...")
    state_manager = StateManager(config.STATE_FILE)
    scraper = DataScraper(state_manager)
    transformer = DataTransformer()
    
    # Ensure output directory exists
    config.DATA_DIR.mkdir(exist_ok=True)
    
    # Clear output file if starting fresh (optional - comment out to append)
    # if config.OUTPUT_FILE.exists() and not state_manager.state.get("total_issues_scraped", 0):
    #     config.OUTPUT_FILE.unlink()
    
    # Get projects to scrape
    projects = config.PROJECTS
    logger.info(f"Projects to scrape: {', '.join(projects)}")
    
    # Batch size for writing to file
    batch_size = 10
    batch = []
    total_transformed = 0
    
    try:
        # Scrape issues
        logger.info("Starting scraping process...")
        for issue in scraper.scrape_all_projects(projects):
            # Transform issue
            transformed = transformer.transform_issue(issue)
            
            if transformed:
                batch.append(transformed)
                total_transformed += 1
                
                # Write in batches
                if len(batch) >= batch_size:
                    if config.OUTPUT_FORMAT == "toon":
                        transformer.save_to_toon(batch, str(config.TOON_OUTPUT_FILE))
                    else:
                        transformer.save_to_jsonl(batch, str(config.OUTPUT_FILE))
                    batch = []
                    logger.info(f"Transformed and saved {total_transformed} issues so far...")
        
        # Write remaining batch
        if batch:
            if config.OUTPUT_FORMAT == "toon":
                transformer.save_to_toon(batch, str(config.TOON_OUTPUT_FILE))
            else:
                transformer.save_to_jsonl(batch, str(config.OUTPUT_FILE))
        
        logger.info("=" * 60)
        logger.info(f"Pipeline completed successfully!")
        logger.info(f"Total issues transformed: {total_transformed}")
        if config.OUTPUT_FORMAT == "toon":
            logger.info(f"Output file (TOON): {config.TOON_OUTPUT_FILE}")
        else:
            logger.info(f"Output file: {config.OUTPUT_FILE}")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user. State saved. Resume by running again.")
        if batch:
            if config.OUTPUT_FORMAT == "toon":
                transformer.save_to_toon(batch, str(config.TOON_OUTPUT_FILE))
            else:
                transformer.save_to_jsonl(batch, str(config.OUTPUT_FILE))
        state_manager.save_state()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        if batch:
            if config.OUTPUT_FORMAT == "toon":
                transformer.save_to_toon(batch, str(config.TOON_OUTPUT_FILE))
            else:
                transformer.save_to_jsonl(batch, str(config.OUTPUT_FILE))
        state_manager.save_state()
        sys.exit(1)


if __name__ == "__main__":
    main()

