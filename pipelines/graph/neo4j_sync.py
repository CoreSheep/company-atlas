"""
Neo4j graph database sync module.
Creates graph relationships between companies based on shared attributes.
"""

import os
import logging
from typing import List, Dict
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jSync:
    """Handles Neo4j graph database synchronization."""
    
    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None
    ):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        logger.info("Connected to Neo4j")
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def create_company_node(self, tx, company: Dict):
        """
        Create or update a company node.
        
        Args:
            tx: Neo4j transaction
            company: Company data dictionary
        """
        query = """
        MERGE (c:Company {company_id: $company_id})
        SET c.company_name = $company_name,
            c.domain = $domain,
            c.industry = $industry,
            c.country = $country,
            c.employee_count = $employee_count,
            c.revenue = $revenue,
            c.founded_year = $founded_year,
            c.source_system = $source_system
        RETURN c
        """
        tx.run(query, **company)
    
    def create_industry_relationship(self, tx, company_id: str, industry: str):
        """
        Create relationship between company and industry.
        
        Args:
            tx: Neo4j transaction
            company_id: Company identifier
            industry: Industry name
        """
        query = """
        MATCH (c:Company {company_id: $company_id})
        MERGE (i:Industry {name: $industry})
        MERGE (c)-[:BELONGS_TO]->(i)
        """
        tx.run(query, company_id=company_id, industry=industry)
    
    def create_country_relationship(self, tx, company_id: str, country: str):
        """
        Create relationship between company and country.
        
        Args:
            tx: Neo4j transaction
            company_id: Company identifier
            country: Country name
        """
        query = """
        MATCH (c:Company {company_id: $company_id})
        MERGE (co:Country {name: $country})
        MERGE (c)-[:LOCATED_IN]->(co)
        """
        tx.run(query, company_id=company_id, country=country)
    
    def create_similar_company_relationships(self, tx, company_id: str, industry: str, country: str):
        """
        Create SIMILAR_TO relationships between companies in same industry/country.
        
        Args:
            tx: Neo4j transaction
            company_id: Company identifier
            industry: Industry name
            country: Country name
        """
        query = """
        MATCH (c1:Company {company_id: $company_id})
        MATCH (c2:Company)
        WHERE c2.industry = $industry 
          AND c2.country = $country 
          AND c2.company_id <> $company_id
        MERGE (c1)-[r:SIMILAR_TO]->(c2)
        ON CREATE SET r.weight = 1
        ON MATCH SET r.weight = r.weight + 1
        """
        tx.run(query, company_id=company_id, industry=industry, country=country)
    
    def sync_unified_companies(self):
        """
        Sync unified companies from Snowflake to Neo4j.
        This would typically query Snowflake unified_companies table.
        """
        logger.info("Starting Neo4j sync...")
        
        # In a real implementation, this would query Snowflake
        # For now, it's a placeholder structure
        
        with self.driver.session() as session:
            # Example: Process companies in batches
            # companies = self._fetch_companies_from_snowflake()
            
            # For demonstration, using a mock structure
            # In production, replace this with actual Snowflake query
            companies = []  # Placeholder
            
            for company in companies:
                session.write_transaction(self.create_company_node, company)
                
                if company.get('industry'):
                    session.write_transaction(
                        self.create_industry_relationship,
                        company['company_id'],
                        company['industry']
                    )
                
                if company.get('country'):
                    session.write_transaction(
                        self.create_country_relationship,
                        company['company_id'],
                        company['country']
                    )
                    
                    session.write_transaction(
                        self.create_similar_company_relationships,
                        company['company_id'],
                        company.get('industry', ''),
                        company['country']
                    )
            
            logger.info(f"Synced {len(companies)} companies to Neo4j")
    
    def query_companies_by_industry(self, industry: str, limit: int = 10) -> List[Dict]:
        """
        Query companies by industry.
        
        Args:
            industry: Industry name
            limit: Maximum number of results
            
        Returns:
            List of company dictionaries
        """
        query = """
        MATCH (c:Company)-[:BELONGS_TO]->(i:Industry {name: $industry})
        RETURN c
        LIMIT $limit
        """
        
        with self.driver.session() as session:
            result = session.run(query, industry=industry, limit=limit)
            return [record['c'] for record in result]
    
    def query_company_network(self, company_id: str, depth: int = 2) -> Dict:
        """
        Query company network with relationships.
        
        Args:
            company_id: Company identifier
            depth: Relationship depth
            
        Returns:
            Company network data
        """
        query = f"""
        MATCH path = (c:Company {{company_id: $company_id}})-[*1..{depth}]-(related)
        RETURN path
        LIMIT 100
        """
        
        with self.driver.session() as session:
            result = session.run(query, company_id=company_id)
            return [record['path'] for record in result]


if __name__ == "__main__":
    # Test Neo4j sync
    neo4j_sync = Neo4jSync()
    neo4j_sync.sync_unified_companies()
    neo4j_sync.close()

